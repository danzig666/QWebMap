"""The "Publish web map" Processing algorithm: the web map of the project's
saved publication settings (Web > Publish Web Map), exported locally or
published to their destination. From a command line (QGIS's own
``qgis_process``, e.g. on Windows ``qgis_process-qgis.bat``)::

    qgis_process run QGIS2VectorTilesFork:publish_web_map --PROJECT_PATH=city.qgz
        [--SETTINGS="City map"] [--ACTION=0|1] [--EXTENT=...] [--OUTPUT_DIR=...]
        [--APPROVE=true] [--SAVE_PROJECT=true]

See publishing.headless for what it does."""

from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputBoolean,
    QgsProcessingOutputFile,
    QgsProcessingOutputFolder,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

from .algorithms import _ICON

# A folder parameter: Qgis.ProcessingFileParameterBehavior (QGIS 3.36+),
# QgsProcessingParameterFile.Folder before.
_FOLDER = getattr(getattr(Qgis, "ProcessingFileParameterBehavior", None), "Folder", None) \
    or QgsProcessingParameterFile.Folder


class PublishWebMapAlgorithm(QgsProcessingAlgorithm):
    """Export or publish the web map of the project's saved settings."""

    SETTINGS = "SETTINGS"
    ACTION = "ACTION"
    EXTENT = "EXTENT"
    OUTPUT_DIR = "OUTPUT_DIR"
    APPROVE = "APPROVE"
    SAVE_PROJECT = "SAVE_PROJECT"
    ACTIONS = ("publish", "export")

    def tr(self, string):  # pylint: disable=invalid-name
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):  # noqa: N802
        return PublishWebMapAlgorithm()

    def name(self):
        return "publish_web_map"

    def displayName(self):  # noqa: N802
        return self.tr("Publish web map (saved settings)")

    def icon(self):
        return _ICON

    def shortHelpString(self):  # noqa: N802
        return self.tr(
            "Exports the web map of the publication settings saved in the project (Web > Publish "
            "Web Map) and publishes it to their destination, as the window's Publish button does; "
            "\"Export locally only\" stops after the local copy. Nothing is asked, so it runs from a "
            "command line: qgis_process run QGIS2VectorTilesFork:publish_web_map "
            "--PROJECT_PATH=map.qgz.\n\n"
            "The extent is the settings' (their layer's extent, or the area last exported) unless "
            "one is given. A publication whose review is due (the first one, or what becomes public "
            "changed) needs \"Approve what becomes public\". Credentials: the saved QGIS "
            "authentication configuration, or the environment variables QWEBMAP_ACCESS_KEY_ID and "
            "QWEBMAP_SECRET_ACCESS_KEY (SSH: QWEBMAP_SSH_PASSWORD, or a key / ssh-agent).")

    def flags(self):
        # The export reads the project on QGIS's main thread (see
        # QGIS2VectorTilesAlgorithm.flags).
        flag_enum = getattr(Qgis, "ProcessingAlgorithmFlag", None)
        no_threading = getattr(flag_enum, "NoThreading", None)
        if no_threading is None:  # QGIS < 3.36
            no_threading = QgsProcessingAlgorithm.FlagNoThreading
        return super().flags() | no_threading

    def initAlgorithm(self, config=None):  # noqa: N802
        self.addParameter(QgsProcessingParameterString(
            self.SETTINGS, self.tr("Publication settings (title or web address; empty = the active ones)"),
            defaultValue="", optional=True))
        self.addParameter(QgsProcessingParameterEnum(
            self.ACTION, self.tr("Action"),
            options=[self.tr("Publish to the settings' destination"), self.tr("Export locally only")],
            defaultValue=0))
        self.addParameter(QgsProcessingParameterExtent(
            self.EXTENT, self.tr("Extent (empty = the settings' extent)"), optional=True))
        self.addParameter(QgsProcessingParameterFile(
            self.OUTPUT_DIR, self.tr("Local folder (empty = the settings' folder)"),
            behavior=_FOLDER, optional=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.APPROVE, self.tr("Approve what becomes public (when the review is due)"),
            defaultValue=False))
        self.addParameter(QgsProcessingParameterBoolean(
            self.SAVE_PROJECT, self.tr("Save the approval and settings into the project file"),
            defaultValue=False))
        self.addOutput(QgsProcessingOutputFolder("OUTPUT_FOLDER", self.tr("Local web map folder")))
        self.addOutput(QgsProcessingOutputFile("ENTRY", self.tr("Local index.html")))
        self.addOutput(QgsProcessingOutputString("URL", self.tr("Public address")))
        self.addOutput(QgsProcessingOutputBoolean("PUBLISHED", self.tr("Published online")))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        from ..publishing import headless  # pylint: disable=import-outside-toplevel
        from ..publishing.errors import PublishingError  # pylint: disable=import-outside-toplevel
        project = context.project()
        if project is None:
            raise QgsProcessingException(self.tr(
                "No project is open: give the project file (qgis_process: --PROJECT_PATH=map.qgz)."))
        try:
            profile = headless.find_profile(project, self.parameterAsString(parameters, self.SETTINGS, context))
            extent = None
            if parameters.get(self.EXTENT):
                rect = self.parameterAsExtent(parameters, self.EXTENT, context)
                crs = self.parameterAsExtentCrs(parameters, self.EXTENT, context)
                extent = headless.extent_3857(project, profile, rect, crs)
            else:
                extent = headless.extent_3857(project, profile)
            upload = self.ACTIONS[self.parameterAsEnum(parameters, self.ACTION, context)] == "publish"
            feedback.pushInfo(self.tr("Web map: {} ({}), destination: {}").format(
                profile.title or profile.slug, profile.slug,
                profile.destination.kind if upload else self.tr("local folder only")))
            result = headless.run(
                project, profile, extent, feedback, upload=upload,
                approve=self.parameterAsBoolean(parameters, self.APPROVE, context),
                output_dir=self.parameterAsString(parameters, self.OUTPUT_DIR, context),
                log=feedback.pushInfo)
        except PublishingError as error:
            detail = f"\n{error.detail}" if error.detail else ""
            raise QgsProcessingException(f"{error.code}: {error.message}{detail}") from error
        for warning in result.warnings:
            feedback.pushWarning(warning)
        feedback.pushInfo(self.tr("Local web map: {}").format(result.entry_path))
        if result.published:
            feedback.pushInfo(self.tr("Published: {}").format(result.url))
            if result.versioned_url:
                feedback.pushInfo(self.tr("This version: {}").format(result.versioned_url))
        if self.parameterAsBoolean(parameters, self.SAVE_PROJECT, context):
            from ..gui import publication_profiles as store  # pylint: disable=import-outside-toplevel
            store.save_profile(project, profile)
            if not project.write():
                feedback.reportError(self.tr("The project file could not be saved: {}").format(
                    project.error()))
        return {"OUTPUT_FOLDER": result.publication_dir, "ENTRY": result.entry_path,
                "URL": result.url, "PUBLISHED": result.published}
