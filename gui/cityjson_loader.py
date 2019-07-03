# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CityJsonLoader
                                 A QGIS plugin
 This plugin allows for CityJSON files to be loaded in QGIS
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2018-06-08
        git sha              : $Format:%H$
        copyright            : (C) 2018 by 3D Geoinformation
        email                : s.vitalis@tudelft.nl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import QAction, QFileDialog, QMessageBox, QDialogButtonBox
from qgis.core import *
from ..loader.layers import DynamicLayerManager, BaseFieldsBuilder, AttributeFieldsDecorator, LodFieldsDecorator, SemanticSurfaceFieldsDecorator, TypeNamingIterator, BaseNamingIterator, LodNamingDecorator, SimpleFeatureBuilder, LodFeatureDecorator, SemanticSurfaceFeatureDecorator
from ..loader.geometry import VerticesCache, GeometryReader
try:
    from qgis._3d import *
    with_3d = True
except ImportError:
    with_3d = False

# Initialize Qt resources from file resources.py
from ..resources import *
# Import the code for the dialog
from .cityjson_loader_dialog import CityJsonLoaderDialog
import os.path
from ..cjio import cityjson

class CityJsonLoader:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CityJsonLoader_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = CityJsonLoaderDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&CityJSON Loader')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'CityJsonLoader')
        self.toolbar.setObjectName(u'CityJsonLoader')

        self.dlg.browseButton.clicked.connect(self.select_cityjson_file)

    def select_cityjson_file(self):
        """Show a dialog to select a CityJSON file."""
        filename, _ = QFileDialog.getOpenFileName(self.dlg,
                                                  "Select CityJSON file",
                                                  "",
                                                  "*.json")
        if filename == "":
            self.clear_file_information()
        else:
            self.dlg.cityjsonPathLineEdit.setText(filename)
            self.update_file_information(filename)

    def clear_file_information(self):
        """Clear all fields related to file information"""
        line_edits = [self.dlg.cityjsonVersionLineEdit,
                      self.dlg.compressedLineEdit,
                      self.dlg.crsLineEdit]
        for line_edit in line_edits:
            line_edit.setText("")
        self.dlg.metadataPlainTextEdit.setPlainText("")
        self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def update_file_information(self, filename):
        """Update metadata fields according to the file provided"""
        try:
            fstream = open(filename)
            model = cityjson.CityJSON(fstream)
            self.dlg.cityjsonVersionLineEdit.setText(model.get_version())
            self.dlg.compressedLineEdit.setText("Yes" if "transform" in model.j else "No")
            if "crs" in model.j["metadata"]:
                self.dlg.crsLineEdit.setText(str(model.j["metadata"]["crs"]["epsg"]))
            else:
                self.dlg.crsLineEdit.setText("None")
            self.dlg.metadataPlainTextEdit.setPlainText(model.get_info())
            self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
        except Exception as error:
            self.dlg.metadataPlainTextEdit.setPlainText("File could not be loaded")
            self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
            raise error

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CityJsonLoader', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/cityjson_loader/cityjson_logo.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load CityJSON...'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&CityJSON Loader'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def load_cityjson(self, filepath):
        """Loads a specified CityJSON file and adds it to the project"""
        file = open(filepath)
        city_model = cityjson.CityJSON(file)

        filename_with_ext = os.path.basename(filepath)
        filename, file_extension = os.path.splitext(filename_with_ext)
        
        multilayer = self.dlg.splitByTypeCheckBox.isChecked()

        city_objects = city_model.j["CityObjects"]

        vertices_cache = VerticesCache()

        if "transform" in city_model.j:
            vertices_cache.set_scale(city_model.j["transform"]["scale"])
            vertices_cache.set_translation(city_model.j["transform"]["translate"])

        # Load the vertices list
        verts = city_model.j["vertices"]
        for v in verts:
            vertices_cache.add_vertex(v)

        geometry_reader = GeometryReader(vertices_cache)

        fields_builder = AttributeFieldsDecorator(BaseFieldsBuilder(), city_model.j)
        feature_builder = SimpleFeatureBuilder(geometry_reader)

        if self.dlg.loDLoadingComboBox.currentIndex() > 0:
            fields_builder = LodFieldsDecorator(fields_builder)
            feature_builder = LodFeatureDecorator(feature_builder, geometry_reader)
        
        if self.dlg.semanticsLoadingCheckBox.isChecked():
            fields_builder = SemanticSurfaceFieldsDecorator(fields_builder)
            feature_builder = SemanticSurfaceFeatureDecorator(feature_builder, geometry_reader)

        if multilayer:
            naming_iterator = TypeNamingIterator(filename, city_model.j)
        else:
            naming_iterator = BaseNamingIterator(filename)
        if self.dlg.loDLoadingComboBox.currentIndex() > 1:
            naming_iterator = LodNamingDecorator(naming_iterator,
                                                 filename,
                                                 city_model.j)

        layer_manager = DynamicLayerManager(city_model.j, feature_builder, naming_iterator, fields_builder)

        layer_manager.prepare_attributes()

        # Iterate through the city objects
        for key, obj in city_objects.items():
            layer_manager.add_object(key, obj)

        # Add the layer(s) to the project
        root = QgsProject.instance().layerTreeRoot()
        group = root.addGroup(filename)
        for vl in layer_manager.get_all_layers():
            QgsProject.instance().addMapLayer(vl ,False)
            group.addLayer(vl)
            
            if with_3d:
                # Add the 3D symbol to the renderer
                material = QgsPhongMaterialSettings()
                material.setDiffuse(vl.renderer().symbol().color())
                
                symbol = QgsPolygon3DSymbol()
                symbol.setMaterial(material)

                renderer = QgsVectorLayer3DRenderer()
                renderer.setLayer(vl)
                renderer.setSymbol(symbol)
                vl.setRenderer3D(renderer)

        
        # Show a message with the outcome of the loading process
        msg = QMessageBox()
        if geometry_reader.skipped_geometries() > 0:
            msg.setIcon(QMessageBox.Warning)
            msg.setText("CityJSON loaded with issues.")
            msg.setInformativeText("Some geometries were skipped.")
            msg.setDetailedText("{} geometries were not surfaces or solids, so could not be loaded.".format(geometry_reader.skipped_geometries()))
        else:
            msg.setIcon(QMessageBox.Information)
            msg.setText("CityJSON loaded successfully.")
        
        msg.setWindowTitle("CityJSON loading finished")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            filepath = self.dlg.cityjsonPathLineEdit.text()
            self.load_cityjson(filepath)
