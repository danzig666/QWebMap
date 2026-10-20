"""Publishing without the Publish window: the web map of a project's saved
publication settings, exported locally or published to their destination
(the "Publish web map" Processing algorithm, so ``qgis_process`` runs it
from a command line). Does what the window's Export locally / Publish
buttons do, with the settings as saved in the project; nothing is asked."""

import datetime as _dt
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle

from .errors import PublishingError
from .models import PublicationProfile
from .profile import disclosure_fingerprint, needs_review, publication_prefix, validate

# Credentials for a run without the QGIS authentication database (e.g. a
# scheduled task): read from the environment, never stored or printed.
ENV_ACCESS_KEY = "QWEBMAP_ACCESS_KEY_ID"
ENV_SECRET_KEY = "QWEBMAP_SECRET_ACCESS_KEY"
ENV_SESSION_TOKEN = "QWEBMAP_SESSION_TOKEN"
ENV_SSH_USER = "QWEBMAP_SSH_USER"
ENV_SSH_PASSWORD = "QWEBMAP_SSH_PASSWORD"


def _codes():
    from .errors import CODES  # pylint: disable=import-outside-toplevel
    return CODES


@dataclass
class HeadlessResult:
    publication_dir: str = ""
    entry_path: str = ""
    url: str = ""
    versioned_url: str = ""
    published: bool = False
    warnings: List[str] = field(default_factory=list)


def saved_profiles(project) -> List[PublicationProfile]:
    from ..gui import publication_profiles as store  # pylint: disable=import-outside-toplevel
    return [profile for profile, _ in store.list_profiles(project)]


def find_profile(project, name: str = "") -> PublicationProfile:
    """The saved settings named ``name`` (title, address or id; any case),
    or the active ones (the ones the Publish window opens with)."""
    from ..gui import publication_profiles as store  # pylint: disable=import-outside-toplevel
    profiles = saved_profiles(project)
    if not profiles:
        raise PublishingError("Q2VT_PUB_PROFILE_INVALID",
                              "The project has no saved publication settings: open Web > Publish Web "
                              "Map once, set the map up and save the settings in the project.")
    wanted = (name or "").strip().casefold()
    if not wanted:
        profile, _ = store.active_profile(project)
        return profile
    for profile in profiles:
        if wanted in {profile.profile_id.casefold(), (profile.slug or "").casefold(),
                      (profile.title or "").strip().casefold()}:
            return profile
    known = ", ".join(f"{p.title or p.slug} ({p.slug})" for p in profiles)
    raise PublishingError("Q2VT_PUB_PROFILE_INVALID",
                          f"No saved publication settings are called {name!r}. Saved: {known}.")


def _to_3857(project, crs, rect: QgsRectangle) -> List[float]:
    transform = QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem("EPSG:3857"), project)
    box = transform.transformBoundingBox(rect)
    return [box.xMinimum(), box.yMinimum(), box.xMaximum(), box.yMaximum()]


def extent_3857(project, profile: PublicationProfile, override: Optional[QgsRectangle] = None,
                override_crs=None) -> List[float]:
    """The area to publish: ``override`` (in ``override_crs``), else the
    settings' extent as the window takes it: the chosen layer's current
    extent, or the fixed extent / the map view last used (saved with the
    settings: there is no map window here)."""
    if override is not None and not override.isEmpty():
        crs = override_crs if override_crs is not None and override_crs.isValid() else project.crs()
        return _to_3857(project, crs, override)
    view = profile.view
    layer = project.mapLayer(view.extent_layer) \
        if view.extent_mode == "layer" and view.extent_layer else None
    if layer is not None:
        box = _to_3857(project, layer.crs(), layer.extent())
        if box[2] > box[0] and box[3] > box[1]:
            return box
    if view.extent:
        return list(view.extent)
    raise PublishingError("Q2VT_PUB_PROFILE_INVALID",
                          "The settings have no extent (they follow the map view, never used yet): "
                          "give one (EXTENT), or export once from the Publish window.")


def live_layers(project, profile: PublicationProfile) -> List[Tuple[str, str]]:
    """[(layer name, tile or WMS address)] of the included raster layers
    the visitors' browsers load live from their own server."""
    from . import live_raster  # pylint: disable=import-outside-toplevel
    out = []
    for config in profile.layers:
        layer = project.mapLayer(config.layer_id) if config.included and config.raster_live else None
        if layer is None or not hasattr(layer, "providerType") or layer.providerType() != "wms":
            continue
        source, _ = live_raster.live_source(layer)
        if source is not None:
            out.append((layer.name(), source["tiles"][0]))
    return out


def live_review_extra(project, profile: PublicationProfile) -> Optional[dict]:
    """The live layers' addresses in the disclosure fingerprint (None
    without any: the fingerprint of earlier approvals stays)."""
    urls = sorted(url for _, url in live_layers(project, profile))
    return {"live": urls} if urls else None


def credentials(profile: PublicationProfile, environ=None):
    """The destination's credentials: from the environment
    (QWEBMAP_ACCESS_KEY_ID / QWEBMAP_SECRET_ACCESS_KEY [/ QWEBMAP_SESSION_TOKEN];
    SSH: QWEBMAP_SSH_PASSWORD [/ QWEBMAP_SSH_USER]), else the saved QGIS
    authentication configuration of the settings (SSH: none needed with a
    key or an agent)."""
    from .credentials import from_auth_config  # pylint: disable=import-outside-toplevel
    from .providers.base import Credentials  # pylint: disable=import-outside-toplevel
    env = os.environ if environ is None else environ
    destination = profile.destination
    if destination.kind == "ssh":
        if env.get(ENV_SSH_PASSWORD):
            return Credentials(env.get(ENV_SSH_USER, "") or destination.user, env[ENV_SSH_PASSWORD])
        return from_auth_config(destination.credential_ref, ssh=True) if destination.credential_ref else None
    if env.get(ENV_ACCESS_KEY) and env.get(ENV_SECRET_KEY):
        return Credentials(env[ENV_ACCESS_KEY], env[ENV_SECRET_KEY], env.get(ENV_SESSION_TOKEN, ""))
    return from_auth_config(destination.credential_ref)


def run(project, profile: PublicationProfile, extent, feedback=None, upload: bool = True,
        approve: bool = False, output_dir: str = "", log=print) -> HeadlessResult:
    """Export the web map of ``profile`` into its local folder (or
    ``output_dir``) and, with ``upload`` and a destination other than
    "local", publish it there. A publication that needs the review (first
    one, or what becomes public changed since the approval) only goes ahead
    with ``approve``: the approval is then recorded in ``profile`` (the
    caller saves it into the project)."""
    from .controller import export_local, publication_dirs  # pylint: disable=import-outside-toplevel
    from .models import ReleaseState  # pylint: disable=import-outside-toplevel
    from .progress import Progress  # pylint: disable=import-outside-toplevel
    if output_dir:
        profile.output.local_directory = output_dir
    if not profile.output.local_directory:
        base = os.path.dirname(project.fileName()) or os.path.expanduser("~")
        profile.output.local_directory = os.path.join(base, "web_maps")
    problems = validate(profile)
    if problems:
        raise PublishingError("Q2VT_PUB_PROFILE_INVALID", "The saved settings have problems:\n"
                              + "\n".join(problems[:12]))
    publishing = upload and profile.destination.kind != "local"
    if publishing:
        extra = live_review_extra(project, profile)
        if needs_review(profile, extra):
            if not approve:
                raise PublishingError(
                    "Q2VT_PUB_REVIEW_NEEDED",
                    "This publication needs the review (the first one, or what becomes public changed "
                    "since it was approved): check it on the Review tab of the Publish window, or run "
                    "again with APPROVE to approve it here.")
            profile.approval.fingerprint = disclosure_fingerprint(profile, extra)
            profile.approval.approved_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
        secrets_of = credentials(profile)  # before the export: a missing one fails fast
    local = export_local(project, profile, QgsRectangle(*extent), feedback)
    result = HeadlessResult(local.publication_dir, local.entry_path, warnings=list(local.warnings))
    if not publishing:
        return result
    from .providers import provider_for  # pylint: disable=import-outside-toplevel
    prefix = "" if profile.destination.kind == "ssh" else publication_prefix(profile)
    provider = provider_for(profile.destination, secrets_of, prefix)
    _, work_dir = publication_dirs(profile)
    secrets = secrets_of.secrets() if secrets_of is not None else []
    progress = Progress(feedback)
    if profile.destination.kind == "ssh":  # one folder, not versioned
        from .folder_publish import publish_folder  # pylint: disable=import-outside-toplevel
        published = publish_folder(local.release, profile, provider, work_dir, progress, secrets=secrets)
    else:
        from .deployments import publish  # pylint: disable=import-outside-toplevel
        published = publish(local.release, profile, provider, work_dir, progress, secrets=secrets)
    for check in published.checks.checks:
        log(f"{'OK' if check.ok else 'FAILED'} {check.name}: {check.detail}")
    result.warnings += list(published.warnings)
    if published.state != ReleaseState.PUBLISHED:
        raise PublishingError(published.code if published.code in _codes() else "Q2VT_PUB_UPLOAD",
                              published.message or f"Publishing ended as {published.state.value}.")
    result.published = True
    result.url, result.versioned_url = published.stable_url, published.versioned_url
    return result
