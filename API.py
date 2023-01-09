bl_info = {
        "name": "blender slicer",
        "description": "full colour slicer for project colour blender",
        "author": "Mark Use Blender00",
        "version": (1, 2, 0),
        "blender": (3, 0, 0),
        "location": "Properties > Render > blender slicer",
        "warning": "", #Used for warning icon and text in add-ons panel
        "support": "COMMUNITY",
        "category": "Render"
        }

import bpy
import bmesh
import mathutils
import math as m
import zipfile
from PIL import Image, ImageMath
import glob
import os
import zipfile
##############################################################################################################
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMessageBox, QComboBox
from PyQt5.QtGui import QPixmap, QColor, QImage
from SerialGRBL import GRBL
from SerialHP45 import HP45
from Interface import Interface
from ImageConverter import ImageConverter
import B64
from numpy import * 
import threading
import time
zpf = "layers.zip"
j=10001 #Layer mameing
layhei = 0.01 #Layer thiccccccc ,in blender units
res = 30 #UV accuritcy, may grately increase slicing time
mar = 2 #Margin(s
ost = -0.0017 #Don't touch unless you know what this do, in blender units
##############################################################################################################
def SLmain(context):
    cslice.slicer(zpf,j,layhei,res,mar,ost)

class FCSlice(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.fcslice"
    bl_label = "slice!"
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        SLmain(context)
        return {'FINISHED'}

def PRmain(context):
    print("not yet implemented")
    #RunPR.runpr()

class FCPrint(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.fcprint"
    bl_label = "print!"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        PRmain(context)
        return {'FINISHED'}

def Premain(context):
    priview.slicer(zpf,j,layhei,res,mar,ost)

class PreSlice(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.preslice"
    bl_label = "preview!"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        Premain(context)
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(SimpleOperator.bl_idname, text=SimpleOperator.bl_label)
#Register and add to the "object" menu (required to also use F3 search "Simple Object Operator" for quick access).
##############################################################################################################
class LayoutDemoPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Project Colour Blender"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Big render button
        layout.label(text="Blender Full-Colour Slicer")
        row = layout.row()
        row.scale_y = 3.0
        row.operator("object.fcslice")
        row = layout.row()
        row.scale_y = 3.0
        row.operator("object.preslice")
        row = layout.row()
        row.scale_y = 3.0
        row.operator("object.fcprint")

##############################################################################################################
#This part of the file is a modified version Oasis controller.
#<https://hackaday.io/project/86954-oasis-3dp>
#Oasis controller is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#Oasis controller is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with Oasis controller.  If not, see <https://www.gnu.org/licenses/>.
class OasisController():
    def __init__(self):
        super(OasisController, self).__init__()        
        self.grbl = GRBL()
        self.Cinkjet = HP45()
        self.Minkjet = HP45()
        self.Yinkjet = HP45()
        self.Binkjet = HP45()
        self.imageconverter = ImageConverter()
        self.layerHeight = 0.1
        self.printing_state = 0 #Whether the printer is printing
        self.printing_abort_flag = 0
        self.printing_pause_flag = 0

        #Grbl connect button
        self.grbl_connection_state = 0 #connected state of grbl
        self.Cinkjet_connection_state = 0 #connected state of inkjet
        self.Minkjet_connection_state = 0 #connected state of inkjet
        self.Yinkjet_connection_state = 0 #connected state of inkjet
        self.Binkjet_connection_state = 0 #connected state of inkjet
        self.file_loaded = 0
        
    def GrblConnect(self, port= ""):
        """Get the GRBL serial port and attempt to connect to it"""
        if (self.grbl_connection_state == 0): #Get connection state, if 0 (not connected)
            #print("Attempting connection with GRBL")
            temp_port = "com"+str(port) #Get text
            temp_succes = self.grbl.Connect(temp_port) #Attempt to connect
            if (temp_succes == 1): #On success, 
                #self.ui.motion_connect.setText("Disconnect") #Rewrite button text
                self.grbl_connection_state = 1 #Set  state
                #self.ui.motion_set_port.clear()
                #start a thread that will update the serial in and output for GRBL
                self._grbl_stop_event = threading.Event()
                self.grbl_update_thread = threading.Thread(target=self.GrblUpdate)
                self.grbl_update_thread.start()
            else:
                print("Connection with GRBL failed")
        else: #On state 1
            #print("disconnecting from GRBL")
            self.grbl.Disconnect() #disconnect
            self.grbl_connection_state = 0 #Set state to disconnected
            #self.ui.motion_connect.setText("Connect") #Rewrite button
            self._grbl_stop_event.set() #Close the grbl serial thread
            
    def GrblUpdate(self):
        """updates serial in and output for the GRBL window"""
        time.sleep(1)
        while not self._grbl_stop_event.is_set():
            grbl_serial_in = str(self.grbl.GetWindowInput())
            grbl_serial_out = str(self.grbl.GetWindowOutput())
            #self.ui.motion_serial_output.moveCursor(QtGui.QTextCursor.End)
            #self.ui.motion_serial_output.insertPlainText(grbl_serial_out)
            #self.ui.motion_serial_output.moveCursor(QtGui.QTextCursor.End)
            #self.ui.motion_serial_input.moveCursor(QtGui.QTextCursor.End)
            #self.ui.motion_serial_input.insertPlainText(grbl_serial_in)
            #self.ui.motion_serial_input.moveCursor(QtGui.QTextCursor.End)
            
            #update state and coordinates
            #self.ui.motion_state.setText(self.grbl.motion_state)
            #self.ui.motion_x_pos.setText(str(self.grbl.motion_x_pos))
            #self.ui.motion_y_pos.setText(str(self.grbl.motion_y_pos))
            #self.ui.motion_b_pos.setText(str(self.grbl.motion_z_pos))
            #self.ui.motion_f_pos.setText(str(self.grbl.motion_a_pos))
            time.sleep(0.2)
##############################################################################################################
    def CInkjetConnect(self, port= ""):
        """Get the inkjet serial port and attempt to connect to it"""
        if (self.Cinkjet_connection_state == 0): #get connection state, if 0 (not connected)
            #print("Attempting connection with HP45")
            temp_port = "com"+port #get text
            temp_succes = self.Cinkjet.Connect(temp_port) #Attempt to connect
            if (temp_succes == 1): #on success, 
                #self.ui.inkjet_connect.setText("Disconnect") #rewrite button text
                self.Cinkjet_connection_state = 1 #set  state
                #self.ui.inkjet_set_port.clear()
                #Start a thread that will update the serial in and output for HP45
                self._Cinkjet_stop_event = threading.Event()
                self.Cinkjet_update_thread = threading.Thread(target=self.CInkjetUpdate)
                self.Cinkjet_update_thread.start()
            else:
                print("Connection with HP failed")
        else: #on state 1
            #print("disconnecting from HP45")
            self.Cinkjet.Disconnect() #Disconnect
            self.Cinkjet_connection_state = 0 #Set state to disconnected
            #self.ui.inkjet_connect.setText("Connect") #rewrite button
            self._Cinkjet_stop_event.set() #Close the HP45 serial thread

    def CInkjetUpdate(self):
        """Updates serial in and output for the inkjet window"""
        time.sleep(1)
        while not self._Cinkjet_stop_event.is_set():
            Cinkjet_serial_in = str(self.Cinkjet.GetWindowInput())
            Cinkjet_serial_out = str(self.Cinkjet.GetWindowOutput())
            #self.ui.inkjet_serial_output.moveCursor(QtGui.QTextCursor.End)
            #self.ui.inkjet_serial_output.insertPlainText(inkjet_serial_out)
            #self.ui.inkjet_serial_output.moveCursor(QtGui.QTextCursor.End)
            #self.ui.inkjet_serial_input.moveCursor(QtGui.QTextCursor.End)
            #self.ui.inkjet_serial_input.insertPlainText(inkjet_serial_in)
            #self.ui.inkjet_serial_input.moveCursor(QtGui.QTextCursor.End)
            
            #update state and coordinates
            #self.ui.inkjet_temperature.setText(str(self.inkjet.inkjet_temperature))
            #self.ui.inkjet_pos.setText(str(self.inkjet.inkjet_x_pos))
            #self.ui.inkjet_writeleft.setText(str(self.inkjet.inkjet_writeleft))
            
            #update inkjet test state
            #self.ui.inkjet_test_state.setText(str(self.inkjet.inkjet_working_nozzles) + "/" + str(self.inkjet.inkjet_total_nozzles))
            time.sleep(0.2)

    #Get the command from the textedit and prints it to Inkjet
    def CInkjetSetPosition(self):
        """Get the position from GRBL, converts it and sends it to HP45"""
        if (self.Cinkjet_connection_state == 1):
            time.sleep(0.3) #Wait for a while to get the newest pos
            temp_pos = self.grbl.motion_y_pos #Set pos to variable
            temp_pos *= 1000.0
            temp_pos = int(temp_pos) #Cast to interger
            self.Cinkjet.SetPosition(temp_pos) #Set position
    
    def CInkjetSetDPI(self):
        """Writes the DPI to the printhead and decode function"""
        #temp_dpi = str(self.ui.inkjet_dpi.text()) #Get text#get dpi
        temp_dpi = "600" #Get text#get dpi
        temp_dpi_val = 0
        temp_success = 0
        try:
            temp_dpi_val = int(temp_dpi)
            temp_success = 1
        except:
            #print ("Unable to convert to dpi")
            nothing = 0

        if (temp_success == 1): #if conversion was successful
            if (self.printing_state == 0): #only set DPI when not printing
                print("DPI to set: " + str(temp_dpi_val))
                if (self.Cinkjet_connection_state == 1): #only write to printhead when connected
                    self.Cinkjet.SetDPI(temp_dpi_val) #write to inkjet
                self.imageconverter.SetDPI(temp_dpi_val) #write to image converter
                if (self.file_loaded != 0): #if any file is loaded
                    print("resising image")
                    self.OpenFile(self.input_file_name[0])
                
    def CInkjetSetDensity(self, temp_density = 0.1):
        """Writes the Density to the printhead"""
        if (self.Cinkjet_connection_state == 1):
            #temp_density = str(self.ui.inkjet_density.text()) #get text #get density
            temp_density_val = 0
            temp_success = 0
            try:
                temp_density_val = int(temp_density)
                temp_success = 1
            except:
                #print ("Unable to convert to dpi")
                nothing = 0

            if (temp_success == 1): #if conversion was successful
                #print("Density to set: " + str(temp_density_val))
                self.Cinkjet.SetDensity(temp_density_val) #write to inkjet

    def MInkjetConnect(self, port= ""):
        """Gets the inkjet serial port and attempt to connect to it"""
        if (self.Minkjet_connection_state == 0): #get connection state, if 0 (not connected)
            #print("Attempting connection with HP45")
            temp_port = "com"+port #get text
            temp_succes = self.Minkjet.Connect(temp_port) #attempt to connect
            if (temp_succes == 1): #on success, 
                #self.ui.inkjet_connect.setText("Disconnect") #rewrite button text
                self.Minkjet_connection_state = 1 #set  state
                #self.ui.inkjet_set_port.clear()
                #start a thread that will update the serial in and output for HP45
                self._Minkjet_stop_event = threading.Event()
                self.Minkjet_update_thread = threading.Thread(target=self.MInkjetUpdate)
                self.Minkjet_update_thread.start()
            else:
                print("Connection with HP failed")
        else: #on state 1
            #print("disconnecting from HP45")
            self.Minkjet.Disconnect() #disconnect
            self.Minkjet_connection_state = 0 #set state to disconnected
            #self.ui.inkjet_connect.setText("Connect") #rewrite button
            self._Minkjet_stop_event.set() #close the HP45 serial thread
            
    def MInkjetUpdate(self):
        """updates serial in and output for the inkjet window"""
        time.sleep(1)
        while not self._Minkjet_stop_event.is_set():
            Minkjet_serial_in = str(self.Minkjet.GetWindowInput())
            Minkjet_serial_out = str(self.Minkjet.GetWindowOutput())
            time.sleep(0.2)

    def MInkjetSetPosition(self):
        """Gets the position from GRBL, converts it and sends it to HP45"""
        if (self.Minkjet_connection_state == 1):
            time.sleep(0.3) #wait for a while to get the newest pos
            temp_pos = self.grbl.motion_y_pos #set pos to variable
            temp_pos *= 1000.0
            temp_pos = int(temp_pos) #cast to interger
            self.Minkjet.SetPosition(temp_pos) #set position
    
    def MInkjetSetDPI(self):
        """Writes the DPI to the printhead and decode function"""
        #temp_dpi = str(self.ui.inkjet_dpi.text()) #get text#get dpi
        temp_dpi = "600" #get text#get dpi
        temp_dpi_val = 0
        temp_success = 0
        try:
            temp_dpi_val = int(temp_dpi)
            temp_success = 1
        except:
            #print ("Unable to convert to dpi")
            nothing = 0

        if (temp_success == 1): #if conversion was successful
            if (self.printing_state == 0): #only set DPI when not printing
                print("DPI to set: " + str(temp_dpi_val))
                if (self.Minkjet_connection_state == 1): #only write to printhead when connected
                    self.Minkjet.SetDPI(temp_dpi_val) #write to inkjet
                self.imageconverter.SetDPI(temp_dpi_val) #write to image converter
                if (self.file_loaded != 0): #if any file is loaded
                    print("resising image")
                    self.OpenFile(self.input_file_name[0])
                
    def MInkjetSetDensity(self, temp_density = 0.1):
        """Writes the Density to the printhead"""
        if (self.Minkjet_connection_state == 1):
            #temp_density = str(self.ui.inkjet_density.text()) #get text #get density
            temp_density_val = 0
            temp_success = 0
            try:
                temp_density_val = int(temp_density)
                temp_success = 1
            except:
                #print ("Unable to convert to dpi")
                nothing = 0
            if (temp_success == 1): #if conversion was successful
                #print("Density to set: " + str(temp_density_val))
                self.Minkjet.SetDensity(temp_density_val) #write to inkjet

    def YInkjetConnect(self, port= ""):
        """Gets the inkjet serial port and attempt to connect to it"""
        if (self.Yinkjet_connection_state == 0): #get connection state, if 0 (not connected)
            #print("Attempting connection with HP45")
            temp_port = "com"+port #get text
            temp_succes = self.Yinkjet.Connect(temp_port) #attempt to connect
            if (temp_succes == 1): #on success, 
                #self.ui.inkjet_connect.setText("Disconnect") #rewrite button text
                self.Yinkjet_connection_state = 1 #set  state
                #self.ui.inkjet_set_port.clear()
                #start a thread that will update the serial in and output for HP45
                self._Yinkjet_stop_event = threading.Event()
                self.Yinkjet_update_thread = threading.Thread(target=self.YInkjetUpdate)
                self.Yinkjet_update_thread.start()
            else:
                print("Connection with HP failed")
        else: #on state 1
            #print("disconnecting from HP45")
            self.Yinkjet.Disconnect() #disconnect
            self.Yinkjet_connection_state = 0 #set state to disconnected
            #self.ui.inkjet_connect.setText("Connect") #rewrite button
            self._Yinkjet_stop_event.set() #close the HP45 serial thread
            
    def YInkjetUpdate(self):
        """updates serial in and output for the inkjet window"""
        time.sleep(1)
        while not self._Yinkjet_stop_event.is_set():
            Yinkjet_serial_in = str(self.Yinkjet.GetWindowInput())
            Yinkjet_serial_out = str(self.Yinkjet.GetWindowOutput())
            time.sleep(0.2)

    def YInkjetSetPosition(self):
        """Gets the position from GRBL, converts it and sends it to HP45"""
        if (self.Yinkjet_connection_state == 1):
            time.sleep(0.3) #wait for a while to get the newest pos
            temp_pos = self.grbl.motion_y_pos #set pos to variable
            temp_pos *= 1000.0
            temp_pos = int(temp_pos) #cast to interger
            self.Yinkjet.SetPosition(temp_pos) #set position
    
    def YInkjetSetDPI(self):
        """Writes the DPI to the printhead and decode function"""
        #temp_dpi = str(self.ui.inkjet_dpi.text()) #get text#get dpi
        temp_dpi = "600" #get text#get dpi
        temp_dpi_val = 0
        temp_success = 0
        try:
            temp_dpi_val = int(temp_dpi)
            temp_success = 1
        except:
            #print ("Unable to convert to dpi")
            nothing = 0

        if (temp_success == 1): #if conversion was successful
            if (self.printing_state == 0): #only set DPI when not printing
                print("DPI to set: " + str(temp_dpi_val))
                if (self.Yinkjet_connection_state == 1): #only write to printhead when connected
                    self.Yinkjet.SetDPI(temp_dpi_val) #write to inkjet
                self.imageconverter.SetDPI(temp_dpi_val) #write to image converter
                if (self.file_loaded != 0): #if any file is loaded
                    print("resising image")
                    self.OpenFile(self.input_file_name[0])
                
    def YInkjetSetDensity(self, temp_density = 0.1):
        """Writes the Density to the printhead"""
        if (self.Yinkjet_connection_state == 1):
            #temp_density = str(self.ui.inkjet_density.text()) #get text #get density
            temp_density_val = 0
            temp_success = 0
            try:
                temp_density_val = int(temp_density)
                temp_success = 1
            except:
                #print ("Unable to convert to dpi")
                nothing = 0

            if (temp_success == 1): #if conversion was successful
                #print("Density to set: " + str(temp_density_val))
                self.Yinkjet.SetDensity(temp_density_val) #write to inkjet

    def BInkjetConnect(self, port= ""):
        """Gets the inkjet serial port and attempt to connect to it"""
        if (self.Binkjet_connection_state == 0): #get connection state, if 0 (not connected)
            #print("Attempting connection with HP45")
            temp_port = "com"+port #get text
            temp_succes = self.Binkjet.Connect(temp_port) #attempt to connect
            if (temp_succes == 1): #on success, 
                #self.ui.inkjet_connect.setText("Disconnect") #rewrite button text
                self.Binkjet_connection_state = 1 #set  state
                #self.ui.inkjet_set_port.clear()
                #start a thread that will update the serial in and output for HP45
                self._Binkjet_stop_event = threading.Event()
                self.Binkjet_update_thread = threading.Thread(target=self.BInkjetUpdate)
                self.Binkjet_update_thread.start()
                
            else:
                print("Connection with HP failed")
        else: #on state 1
            #print("disconnecting from HP45")
            self.Binkjet.Disconnect() #disconnect
            self.Binkjet_connection_state = 0 #set state to disconnected
            #self.ui.inkjet_connect.setText("Connect") #rewrite button
            self._Binkjet_stop_event.set() #close the HP45 serial thread
            
    def BInkjetUpdate(self):
        """updates serial in and output for the inkjet window"""
        time.sleep(1)
        while not self._Binkjet_stop_event.is_set():
            Binkjet_serial_in = str(self.Binkjet.GetWindowInput())
            Binkjet_serial_out = str(self.Binkjet.GetWindowOutput())
            time.sleep(0.2)

    def BInkjetSetPosition(self):
        """Gets the position from GRBL, converts it and sends it to HP45"""
        if (self.Binkjet_connection_state == 1):
            time.sleep(0.3) #wait for a while to get the newest pos
            temp_pos = self.grbl.motion_y_pos #set pos to variable
            temp_pos *= 1000.0
            temp_pos = int(temp_pos) #cast to interger
            self.Binkjet.SetPosition(temp_pos) #set position
    
    def BInkjetSetDPI(self):
        """Writes the DPI to the printhead and decode function"""
        #temp_dpi = str(self.ui.inkjet_dpi.text()) #get text#get dpi
        temp_dpi = "600" #get text#get dpi
        temp_dpi_val = 0
        temp_success = 0
        try:
            temp_dpi_val = int(temp_dpi)
            temp_success = 1
        except:
            #print ("Unable to convert to dpi")
            nothing = 0
        if (temp_success == 1): #if conversion was successful
            if (self.printing_state == 0): #only set DPI when not printing
                print("DPI to set: " + str(temp_dpi_val))
                if (self.Binkjet_connection_state == 1): #only write to printhead when connected
                    self.Binkjet.SetDPI(temp_dpi_val) #write to inkjet
                self.imageconverter.SetDPI(temp_dpi_val) #write to image converter
                if (self.file_loaded != 0): #if any file is loaded
                    print("resising image")
                    self.OpenFile(self.input_file_name[0])
                
    def BInkjetSetDensity(self, temp_density = 0.1):
        """Writes the Density to the printhead"""
        if (self.Binkjet_connection_state == 1):
            #temp_density = str(self.ui.inkjet_density.text()) #get text #get density
            temp_density_val = 0
            temp_success = 0
            try:
                temp_density_val = int(temp_density)
                temp_success = 1
            except:
                #print ("Unable to convert to dpi")
                nothing = 0
            if (temp_success == 1): #if conversion was successful
                #print("Density to set: " + str(temp_density_val))
                self.Binkjet.SetDensity(temp_density_val) #write to inkjet
##############################################################################################################                
    def GRBLSpreader(self):
        """Toggles the spreader on or off and sets the button"""
        temp_return = self.grbl.SpreaderToggle()

    def GRBLNewLayer(self):
        """add a new layer"""
        if (self.grbl_connection_state == 1):
            #print("new layer")
            #to do: read layer thickness
            #temp_layer_thickness = str(self.ui.motion_layer_thickness.text())
            temp_layer_thickness = self.layerHeight
            temp_layer_thickness_val = 0
            temp_success = 0
            try:
                temp_layer_thickness_val = float(temp_layer_thickness)
                temp_success = 1
            except:
                #print ("Unable to convert to layer thickness")
                nothing = 0
            if (temp_success == 1):
                #print("adding new layer: " + str(temp_layer_thickness_val))
                self.grbl.NewLayer(temp_layer_thickness_val)
                
    def GRBLPrimeLayer(self):
        """add a new layer"""
        if (self.grbl_connection_state == 1):
            #print("new layer")
            #to do: read layer thickness
            #temp_layer_thickness = str(self.ui.motion_layer_thickness.text())
            temp_layer_thickness = self.layerHeight
            temp_layer_thickness_val = 0
            temp_success = 0
            try:
                temp_layer_thickness_val = float(temp_layer_thickness)
                temp_success = 1
            except:
                #print ("Unable to convert to layer thickness")
                nothing = 0
            if (temp_success == 1):
                #print("adding new layer: " + str(temp_layer_thickness_val))
                self.grbl.NewLayer(temp_layer_thickness_val, 1)
    
    def OpenFile(self, temp_input_file = ""):
        """Opens a file dialog, takes the filepath, and passes it to the image converter"""
        if (temp_input_file):
            temp_response = self.imageconverter.OpenFile(temp_input_file)
        if (temp_response == 1):
            self.RenderInput()
            self.file_loaded = 1
        if (temp_response == 2):
            self.file_loaded = 2
            #self.ui.layer_slider.setMaximum(self.imageconverter.svg_layers-1)
            self.RenderOutput()
            
    def PausePrint(self):
        if (self.file_loaded == 2 ): #only update pause if print is running
            if(self.printing_pause_flag == 0):
                self.printing_pause_flag = 1
                #self.ui.pause_button.setText("Resume")
            else:
                self.printing_pause_flag = 0
                #self.ui.pause_button.setText("Pause")
                
    def AbortPrint(self):
        if (self.file_loaded == 2): #only update pause if print is running
            #MessageBox.about(self, "Title", "Message")
            #temp_response = QMessageBox.question(self, 'Abort print', "Do you really want to abort the print?",QMessageBox.Yes | QMessageBox.No)
            if (temp_response == QMessageBox.Yes):
                self.printing_abort_flag = 1
            
    def RunPrintArray(self):
        """Starts a thread for the print array function"""
        if (self.file_loaded == 1):
            self._printing_stop_event = threading.Event()
            self.printing_thread = threading.Thread(target=self.PrintArray)
            self.printing_thread.start()
##############################################################################################################    
    def CPrintArray(self):
        """Prints the current converted image array, only works if both inkjet and motion are connected"""
        #y is sweep direction, x is gantry direction
        #Width is Y direction, height is X direction
        #check if printhead and motion are connected
        if (self.grbl_connection_state == 0): #do not continue if motion is not connected
            return
        #inkjet is ignored for now
            
        #make universal variables
        self.Cinkjet_line_buffer = [] #buffer storing the print lines
        self.Cinkjet_lines_left = 0 #the number of lines in buffer
        self.Cinkjet_line_history = "" #the last burst line sent to buffer
        self.travel_speed = 12000.0
        self.print_speed = 3000.0
        self.Cinkjet.ClearBuffer() #clear inkjet buffer on HP45
        self.grbl.Home() #home gantry
        
        #look for X-min and X-max in image 
        self.sweep_x_min = 0
        self.sweep_x_max = 0
        temp_break_loop = 0
        #loop through image
        for h in range(0,self.imageconverter.image_array_height):
            for w in range(0,self.imageconverter.image_array_width):
                if (self.imageconverter.image_array[h][w] != 0):
                    self.sweep_x_min = h
                    temp_break_loop = 1
                    print("X-min on row: " + str(h))
                    break
            if (temp_break_loop == 1):
                break
        temp_break_loop = 0
        for h in reversed(range(0,self.imageconverter.image_array_height)):
            for w in range(0,self.imageconverter.image_array_width):
                if (self.imageconverter.image_array[h][w] != 0):
                    self.sweep_x_max = h
                    temp_break_loop = 1
                    print("X-max on row: " + str(h))
                    break
            if (temp_break_loop == 1):
                break
                
        #set X start pixel, X pixel step (using current DPI)
        self.sweep_size = int(self.imageconverter.GetDPI() / 2) #get sweep size (is halve of DPI)
        print("Sweep size: " + str(self.sweep_size))

        #determine pixel to position multiplier (in millimeters)
        self.pixel_to_pos_multiplier = 25.4 / self.imageconverter.GetDPI() 

        #determine x and y start position (in millimeters)
        self.y_start_pos = 100.0
        self.x_start_pos = 150.0
        self.y_acceleration_distance = 25.0
        self.sweep_x_min_pos = self.sweep_x_min

        ###loop through all sweeps
        temp_sweep_stop = 0
        while (temp_sweep_stop == 0):
            #determine if there still is a sweep left
            #determine X-start and X end of sweep
            if (self.sweep_x_min_pos + self.sweep_size <= self.sweep_x_max):
                self.sweep_x_max_pos = self.sweep_x_min_pos + self.sweep_size
            else:
                self.sweep_x_max_pos = self.sweep_x_max #set max of image as max pos
                temp_sweep_stop = 1 #mark last loop
            print("Sweep from: " + str(self.sweep_x_min_pos) + ", to: " + str(self.sweep_x_max_pos))
            
            #Look for Y min and Y max in sweep
            self.sweep_y_min = 0
            self.sweep_y_max = 0

            #get Y min
            temp_break_loop = 0
            for w in range(self.imageconverter.image_array_width):
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    if (self.imageconverter.image_array[h][w] != 0):
                        self.sweep_y_min = w
                        temp_break_loop = 1
                        break
                if (temp_break_loop == 1):
                    break

            #get Y max
            temp_break_loop = 0
            for w in reversed(range(self.imageconverter.image_array_width)):
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    if (self.imageconverter.image_array[h][w] != 0):
                        self.sweep_y_max = w
                        temp_break_loop = 1
                        break
                if (temp_break_loop == 1):
                    break
            print("sweep Y min: " + str(self.sweep_y_min) +", Y max: " + str(self.sweep_y_max))
            
            #determine printing direction (if necessary)
            self.printing_direction = 1 #only 1 for now
            
            #Set Y at starting and end position
            if (self.printing_direction == 1):
                self.y_printing_start_pos = self.sweep_y_min * self.pixel_to_pos_multiplier
                self.y_printing_start_pos += self.y_start_pos - self.y_acceleration_distance
                self.y_printing_end_pos = self.sweep_y_max * self.pixel_to_pos_multiplier
                self.y_printing_end_pos += self.y_start_pos + self.y_acceleration_distance
                print("Sweep ranges from: " + str(self.y_printing_start_pos) + "mm, to: " + str(self.y_printing_end_pos) + "mm")
            
            #set X position
            self.x_printing_pos = self.sweep_x_min_pos * self.pixel_to_pos_multiplier
            self.x_printing_pos += self.x_start_pos
            
            #fill local print buffer with lines
            print("Filling local buffer with inkjet")
            temp_line_history = ""
            temp_line_string = ""
            temp_line_array = zeros(self.sweep_size)
            temp_line_history = B64.B64ToArray(temp_line_array) #make first history 0
            temp_line_string = temp_line_history #make string also 0
            
            #add all of starter cap at the front
            if (self.printing_direction == 1):
                temp_pos = ((self.sweep_y_min - 1) * self.pixel_to_pos_multiplier) + self.y_start_pos
                temp_pos *= 1000 #printhead pos is in microns
                temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                self.Cinkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                self.Cinkjet_lines_left += 1
            for w in range(self.sweep_y_min,self.sweep_y_max):
                #print("Parsing line: " + str(w))
                temp_line_changed = 0 #reset changed
                temp_counter = 0
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    #loop through all pixels to make a new burst
                    temp_line_array[temp_counter] = self.imageconverter.image_array[h][w] #write array value to temp
                    temp_counter += 1
                temp_line_string = B64.B64ToArray(temp_line_array) #convert to string
                if (temp_line_string != temp_line_history):
                    #print("line changed on pos: " + str(w))
                    temp_line_history = temp_line_string
                    #add line to buffer
                    temp_pos = (w * self.pixel_to_pos_multiplier) + self.y_start_pos
                    temp_pos *= 1000 #printhead pos is in microns
                    temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                    self.Cinkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                    self.Cinkjet_lines_left += 1
            
            #add all off cap at the end of the image
            temp_line_array = zeros(self.sweep_size)
            temp_line_string = B64.B64ToArray(temp_line_array)
            if (self.printing_direction == 1):
                temp_pos = ((self.sweep_y_max + 1) * self.pixel_to_pos_multiplier) + self.y_start_pos
                temp_pos *= 1000 #printhead pos is in microns
                temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                self.Cinkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                self.Cinkjet_lines_left += 1
            
            print("Making printing buffer done: ")
            #print(self.inkjet_line_buffer)
            
            #wait till the head is idle
            while (self.grbl.motion_state != 'idle'):
                nothing = 0
            print("break from idle, moving to filling buffers")
            
            #match inkjet and printer pos
            self.CInkjetSetPosition()
            
            #Fill inkjet buffer with with sweep lines
            print("Filling inkjet buffer")
            #start filling the inkjet buffer on the HP45 lines
            temp_lines_sent = 0
            while(True):
                if (self.Cinkjet_lines_left > 0):
                    self.Cinkjet.SerialWriteBufferRaw(self.Cinkjet_line_buffer[0])
                    #time.sleep(0.001) #this is a good replacement for print, but takes forever
                    print(str(self.Cinkjet_line_buffer[0])) #some sort of delay is required, else the function gets filled up too quickly. Will move to different buffer later
                    del self.Cinkjet_line_buffer[0] #remove sent line
                    self.Cinkjet_lines_left -= 1
                    temp_lines_sent += 1
                else:
                    break
            
            #send motion lines
            print("Filling motion buffer")
            self.grbl.SerialGotoXY(self.x_printing_pos, self.y_printing_start_pos, self.travel_speed)
            self.grbl.SerialGotoXY(self.x_printing_pos, self.y_printing_end_pos, self.print_speed) 
            self.grbl.StatusIndexSet() #set current status index 
            while (True):
                if (self.grbl.StatusIndexChanged() == 1 and self.grbl.motion_state == 'idle'):
                    print("break conditions for print while loop")
                    break #break if exit conditions met
            self.sweep_x_min_pos += self.sweep_size
        ###end of loop through sweep
        #repeat loop until all sweeps are finished
        print("Printing done")
        #home gantry
        #self.grbl.Home() #home gantry    
    
    def MPrintArray(self):
        """Prints the current converted image array, only works if both inkjet and motion are connected"""
        #y is sweep direction, x is gantry direction
        #Width is Y direction, height is X direction
        
        #check if printhead and motion are connected
        if (self.grbl_connection_state == 0): #do not continue if motion is not connected
            return
        #inkjet is ignored for now
        
        #make universal variables
        self.Minkjet_line_buffer = [] #buffer storing the print lines
        self.Minkjet_lines_left = 0 #the number of lines in buffer
        self.Minkjet_line_history = "" #the last burst line sent to buffer
        self.travel_speed = 12000.0
        self.print_speed = 3000.0
        self.Minkjet.ClearBuffer() #clear inkjet buffer on HP45
        self.grbl.Home() #home gantry
        
        #look for X-min and X-max in image 
        self.sweep_x_min = 0
        self.sweep_x_max = 0
        temp_break_loop = 0
        #loop through image
        for h in range(0,self.imageconverter.image_array_height):
            for w in range(0,self.imageconverter.image_array_width):
                if (self.imageconverter.image_array[h][w] != 0):
                    self.sweep_x_min = h
                    temp_break_loop = 1
                    print("X-min on row: " + str(h))
                    break
            if (temp_break_loop == 1):
                break
        temp_break_loop = 0
        for h in reversed(range(0,self.imageconverter.image_array_height)):
            for w in range(0,self.imageconverter.image_array_width):
                if (self.imageconverter.image_array[h][w] != 0):
                    self.sweep_x_max = h
                    temp_break_loop = 1
                    print("X-max on row: " + str(h))
                    break
            if (temp_break_loop == 1):
                break
                
        #set X start pixel, X pixel step (using current DPI)
        self.sweep_size = int(self.imageconverter.GetDPI() / 2) #get sweep size (is halve of DPI)
        print("Sweep size: " + str(self.sweep_size))
        #determine pixel to position multiplier (in millimeters)
        self.pixel_to_pos_multiplier = 25.4 / self.imageconverter.GetDPI() 
        #determine x and y start position (in millimeters)
        self.y_start_pos = 100.0
        self.x_start_pos = 150.0
        self.y_acceleration_distance = 25.0
        self.sweep_x_min_pos = self.sweep_x_min
        ###loop through all sweeps
        temp_sweep_stop = 0
        while (temp_sweep_stop == 0):
            #determine if there still is a sweep left
            #determine X-start and X end of sweep
            if (self.sweep_x_min_pos + self.sweep_size <= self.sweep_x_max):
                self.sweep_x_max_pos = self.sweep_x_min_pos + self.sweep_size
            else:
                self.sweep_x_max_pos = self.sweep_x_max #set max of image as max pos
                temp_sweep_stop = 1 #mark last loop
            print("Sweep from: " + str(self.sweep_x_min_pos) + ", to: " + str(self.sweep_x_max_pos))
            
            #Look for Y min and Y max in sweep
            self.sweep_y_min = 0
            self.sweep_y_max = 0
            #get Y min
            temp_break_loop = 0
            for w in range(self.imageconverter.image_array_width):
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    if (self.imageconverter.image_array[h][w] != 0):
                        self.sweep_y_min = w
                        temp_break_loop = 1
                        break
                if (temp_break_loop == 1):
                    break
            #get Y max
            temp_break_loop = 0
            for w in reversed(range(self.imageconverter.image_array_width)):
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    if (self.imageconverter.image_array[h][w] != 0):
                        self.sweep_y_max = w
                        temp_break_loop = 1
                        break
                if (temp_break_loop == 1):
                    break
            print("sweep Y min: " + str(self.sweep_y_min) +", Y max: " + str(self.sweep_y_max))
            
            #determine printing direction (if necessary)
            self.printing_direction = 1 #only 1 for now
            
            #Set Y at starting and end position
            if (self.printing_direction == 1):
                self.y_printing_start_pos = self.sweep_y_min * self.pixel_to_pos_multiplier
                self.y_printing_start_pos += self.y_start_pos - self.y_acceleration_distance
                self.y_printing_end_pos = self.sweep_y_max * self.pixel_to_pos_multiplier
                self.y_printing_end_pos += self.y_start_pos + self.y_acceleration_distance
                print("Sweep ranges from: " + str(self.y_printing_start_pos) + "mm, to: " + str(self.y_printing_end_pos) + "mm")
            
            #set X position
            self.x_printing_pos = self.sweep_x_min_pos * self.pixel_to_pos_multiplier
            self.x_printing_pos += self.x_start_pos
            
            #fill local print buffer with lines
            print("Filling local buffer with inkjet")
            temp_line_history = ""
            temp_line_string = ""
            temp_line_array = zeros(self.sweep_size)
            temp_line_history = B64.B64ToArray(temp_line_array) #make first history 0
            temp_line_string = temp_line_history #make string also 0
            
            #add all of starter cap at the front
            if (self.printing_direction == 1):
                temp_pos = ((self.sweep_y_min - 1) * self.pixel_to_pos_multiplier) + self.y_start_pos
                temp_pos *= 1000 #printhead pos is in microns
                temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                self.Minkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                self.Minkjet_lines_left += 1
                
            for w in range(self.sweep_y_min,self.sweep_y_max):
                #print("Parsing line: " + str(w))
                temp_line_changed = 0 #reset changed
                temp_counter = 0
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    #loop through all pixels to make a new burst
                    temp_line_array[temp_counter] = self.imageconverter.image_array[h][w] #write array value to temp
                    
                    temp_counter += 1
                temp_line_string = B64.B64ToArray(temp_line_array) #convert to string
                if (temp_line_string != temp_line_history):
                    #print("line changed on pos: " + str(w))
                    temp_line_history = temp_line_string
                    #add line to buffer
                    temp_pos = (w * self.pixel_to_pos_multiplier) + self.y_start_pos
                    temp_pos *= 1000 #printhead pos is in microns
                    temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                    self.Minkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                    self.Minkjet_lines_left += 1
            
            #add all off cap at the end of the image
            temp_line_array = zeros(self.sweep_size)
            temp_line_string = B64.B64ToArray(temp_line_array)
            if (self.printing_direction == 1):
                temp_pos = ((self.sweep_y_max + 1) * self.pixel_to_pos_multiplier) + self.y_start_pos
                temp_pos *= 1000 #printhead pos is in microns
                temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                self.Minkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                self.Minkjet_lines_left += 1
                
            print("Making printing buffer done: ")
            #print(self.inkjet_line_buffer)
            
            #wait till the head is idle
            while (self.grbl.motion_state != 'idle'):
                nothing = 0
            print("break from idle, moving to filling buffers")
            
            #match inkjet and printer pos
            self.MInkjetSetPosition()
            
            #Fill inkjet buffer with with sweep lines
            print("Filling inkjet buffer")
            #start filling the inkjet buffer on the HP45 lines
            temp_lines_sent = 0
            while(True):
                if (self.Minkjet_lines_left > 0):
                    self.Minkjet.SerialWriteBufferRaw(self.Minkjet_line_buffer[0])
                    #time.sleep(0.001) #this is a good replacement for print, but takes forever
                    print(str(self.Minkjet_line_buffer[0])) #some sort of delay is required, else the function gets filled up too quickly. Will move to different buffer later
                    del self.Minkjet_line_buffer[0] #remove sent line
                    self.Minkjet_lines_left -= 1
                    temp_lines_sent += 1
                else:
                    break
            
            #send motion lines
            print("Filling motion buffer")
            self.grbl.SerialGotoXY(self.x_printing_pos, self.y_printing_start_pos, self.travel_speed)
            self.grbl.SerialGotoXY(self.x_printing_pos, self.y_printing_end_pos, self.print_speed) 
            self.grbl.StatusIndexSet() #set current status index 
            
            while (True):
                if (self.grbl.StatusIndexChanged() == 1 and self.grbl.motion_state == 'idle'):
                    print("break conditions for print while loop")
                    break #break if exit conditions met
            
            self.sweep_x_min_pos += self.sweep_size
        ###end of loop through sweep
        #repeat loop until all sweeps are finished
        print("Printing done")
        #home gantry
        #self.grbl.Home() #home gantry

    def YPrintArray(self):
        """Prints the current converted image array, only works if both inkjet and motion are connected"""
        #y is sweep direction, x is gantry direction
        #Width is Y direction, height is X direction
        
        #check if printhead and motion are connected
        if (self.grbl_connection_state == 0): #do not continue if motion is not connected
            return
        #inkjet is ignored for now
        
        #make universal variables
        self.Yinkjet_line_buffer = [] #buffer storing the print lines
        self.Yinkjet_lines_left = 0 #the number of lines in buffer
        self.Yinkjet_line_history = "" #the last burst line sent to buffer
        self.travel_speed = 12000.0
        self.print_speed = 3000.0
        self.Yinkjet.ClearBuffer() #clear inkjet buffer on HP45
        self.grbl.Home() #home gantry
        
        #look for X-min and X-max in image 
        self.sweep_x_min = 0
        self.sweep_x_max = 0
        temp_break_loop = 0
        #loop through image
        for h in range(0,self.imageconverter.image_array_height):
            for w in range(0,self.imageconverter.image_array_width):
                if (self.imageconverter.image_array[h][w] != 0):
                    self.sweep_x_min = h
                    temp_break_loop = 1
                    print("X-min on row: " + str(h))
                    break
            if (temp_break_loop == 1):
                break
        temp_break_loop = 0
        for h in reversed(range(0,self.imageconverter.image_array_height)):
            for w in range(0,self.imageconverter.image_array_width):
                if (self.imageconverter.image_array[h][w] != 0):
                    self.sweep_x_max = h
                    temp_break_loop = 1
                    print("X-max on row: " + str(h))
                    break
            if (temp_break_loop == 1):
                break
                
        #set X start pixel, X pixel step (using current DPI)
        self.sweep_size = int(self.imageconverter.GetDPI() / 2) #get sweep size (is halve of DPI)
        print("Sweep size: " + str(self.sweep_size))
        #determine pixel to position multiplier (in millimeters)
        self.pixel_to_pos_multiplier = 25.4 / self.imageconverter.GetDPI() 
        #determine x and y start position (in millimeters)
        self.y_start_pos = 100.0
        self.x_start_pos = 150.0
        self.y_acceleration_distance = 25.0
        self.sweep_x_min_pos = self.sweep_x_min
        ###loop through all sweeps
        temp_sweep_stop = 0
        while (temp_sweep_stop == 0):
            #determine if there still is a sweep left
            #determine X-start and X end of sweep
            if (self.sweep_x_min_pos + self.sweep_size <= self.sweep_x_max):
                self.sweep_x_max_pos = self.sweep_x_min_pos + self.sweep_size
            else:
                self.sweep_x_max_pos = self.sweep_x_max #set max of image as max pos
                temp_sweep_stop = 1 #mark last loop
            print("Sweep from: " + str(self.sweep_x_min_pos) + ", to: " + str(self.sweep_x_max_pos))
            
            #Look for Y min and Y max in sweep
            self.sweep_y_min = 0
            self.sweep_y_max = 0
            #get Y min
            temp_break_loop = 0
            for w in range(self.imageconverter.image_array_width):
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    if (self.imageconverter.image_array[h][w] != 0):
                        self.sweep_y_min = w
                        temp_break_loop = 1
                        break
                if (temp_break_loop == 1):
                    break
            #get Y max
            temp_break_loop = 0
            for w in reversed(range(self.imageconverter.image_array_width)):
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    if (self.imageconverter.image_array[h][w] != 0):
                        self.sweep_y_max = w
                        temp_break_loop = 1
                        break
                if (temp_break_loop == 1):
                    break
            print("sweep Y min: " + str(self.sweep_y_min) +", Y max: " + str(self.sweep_y_max))
            
            #determine printing direction (if necessary)
            self.printing_direction = 1 #only 1 for now
            
            #Set Y at starting and end position
            if (self.printing_direction == 1):
                self.y_printing_start_pos = self.sweep_y_min * self.pixel_to_pos_multiplier
                self.y_printing_start_pos += self.y_start_pos - self.y_acceleration_distance
                self.y_printing_end_pos = self.sweep_y_max * self.pixel_to_pos_multiplier
                self.y_printing_end_pos += self.y_start_pos + self.y_acceleration_distance
                print("Sweep ranges from: " + str(self.y_printing_start_pos) + "mm, to: " + str(self.y_printing_end_pos) + "mm")
            
            #set X position
            self.x_printing_pos = self.sweep_x_min_pos * self.pixel_to_pos_multiplier
            self.x_printing_pos += self.x_start_pos
            
            #fill local print buffer with lines
            print("Filling local buffer with inkjet")
            temp_line_history = ""
            temp_line_string = ""
            temp_line_array = zeros(self.sweep_size)
            temp_line_history = B64.B64ToArray(temp_line_array) #make first history 0
            temp_line_string = temp_line_history #make string also 0

            #add all of starter cap at the front
            if (self.printing_direction == 1):
                temp_pos = ((self.sweep_y_min - 1) * self.pixel_to_pos_multiplier) + self.y_start_pos
                temp_pos *= 1000 #printhead pos is in microns
                temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                self.Yinkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                self.Yinkjet_lines_left += 1
                
            for w in range(self.sweep_y_min,self.sweep_y_max):
                #print("Parsing line: " + str(w))
                temp_line_changed = 0 #reset changed
                temp_counter = 0
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    #loop through all pixels to make a new burst
                    temp_line_array[temp_counter] = self.imageconverter.image_array[h][w] #write array value to temp
                    temp_counter += 1
                temp_line_string = B64.B64ToArray(temp_line_array) #convert to string
                if (temp_line_string != temp_line_history):
                    #print("line changed on pos: " + str(w))
                    temp_line_history = temp_line_string
                    #add line to buffer
                    temp_pos = (w * self.pixel_to_pos_multiplier) + self.y_start_pos
                    temp_pos *= 1000 #printhead pos is in microns
                    temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                    self.Yinkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                    self.Yinkjet_lines_left += 1
            #add all off cap at the end of the image
            temp_line_array = zeros(self.sweep_size)
            temp_line_string = B64.B64ToArray(temp_line_array)
            if (self.printing_direction == 1):
                temp_pos = ((self.sweep_y_max + 1) * self.pixel_to_pos_multiplier) + self.y_start_pos
                temp_pos *= 1000 #printhead pos is in microns
                temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                self.Yinkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                self.Yinkjet_lines_left += 1
            print("Making printing buffer done: ")
            #print(self.inkjet_line_buffer)
            #wait till the head is idle
            while (self.grbl.motion_state != 'idle'):
                nothing = 0
            print("break from idle, moving to filling buffers")
            #match inkjet and printer pos
            self.YInkjetSetPosition()
            #Fill inkjet buffer with with sweep lines
            print("Filling inkjet buffer")
            #start filling the inkjet buffer on the HP45 lines
            temp_lines_sent = 0
            while(True):
                if (self.Yinkjet_lines_left > 0):
                    self.Yinkjet.SerialWriteBufferRaw(self.Yinkjet_line_buffer[0])
                    #time.sleep(0.001) #this is a good replacement for print, but takes forever
                    print(str(self.Yinkjet_line_buffer[0])) #some sort of delay is required, else the function gets filled up too quickly. Will move to different buffer later
                    del self.Yinkjet_line_buffer[0] #remove sent line
                    self.Yinkjet_lines_left -= 1
                    temp_lines_sent += 1
                else:
                    break
            #send motion lines
            print("Filling motion buffer")
            self.grbl.SerialGotoXY(self.x_printing_pos, self.y_printing_start_pos, self.travel_speed)
            self.grbl.SerialGotoXY(self.x_printing_pos, self.y_printing_end_pos, self.print_speed) 
            self.grbl.StatusIndexSet() #set current status index 
            while (True):
                if (self.grbl.StatusIndexChanged() == 1 and self.grbl.motion_state == 'idle'):
                    print("break conditions for print while loop")
                    break #break if exit conditions met
            self.sweep_x_min_pos += self.sweep_size
        ###end of loop through sweep
        #repeat loop until all sweeps are finished
        print("Printing done")
        #home gantry
        #self.grbl.Home() #home gantry
    def BPrintArray(self):
        """Prints the current converted image array, only works if both inkjet and motion are connected"""
        #y is sweep direction, x is gantry direction
        #Width is Y direction, height is X direction
        
        #check if printhead and motion are connected
        if (self.grbl_connection_state == 0): #do not continue if motion is not connected
            return
        #inkjet is ignored for now
        #make universal variables
        self.Binkjet_line_buffer = [] #buffer storing the print lines
        self.Binkjet_lines_left = 0 #the number of lines in buffer
        self.Binkjet_line_history = "" #the last burst line sent to buffer
        self.travel_speed = 12000.0
        self.print_speed = 3000.0
        self.Binkjet.ClearBuffer() #clear inkjet buffer on HP45
        self.grbl.Home() #home gantry
        #look for X-min and X-max in image 
        self.sweep_x_min = 0
        self.sweep_x_max = 0
        temp_break_loop = 0
        #loop through image
        for h in range(0,self.imageconverter.image_array_height):
            for w in range(0,self.imageconverter.image_array_width):
                if (self.imageconverter.image_array[h][w] != 0):
                    self.sweep_x_min = h
                    temp_break_loop = 1
                    print("X-min on row: " + str(h))
                    break
            if (temp_break_loop == 1):
                break
        temp_break_loop = 0
        for h in reversed(range(0,self.imageconverter.image_array_height)):
            for w in range(0,self.imageconverter.image_array_width):
                if (self.imageconverter.image_array[h][w] != 0):
                    self.sweep_x_max = h
                    temp_break_loop = 1
                    print("X-max on row: " + str(h))
                    break
            if (temp_break_loop == 1):
                break
        #set X start pixel, X pixel step (using current DPI)
        self.sweep_size = int(self.imageconverter.GetDPI() / 2) #get sweep size (is halve of DPI)
        print("Sweep size: " + str(self.sweep_size))
        #determine pixel to position multiplier (in millimeters)
        self.pixel_to_pos_multiplier = 25.4 / self.imageconverter.GetDPI() 
        #determine x and y start position (in millimeters)
        self.y_start_pos = 100.0
        self.x_start_pos = 150.0
        self.y_acceleration_distance = 25.0
        self.sweep_x_min_pos = self.sweep_x_min
        ###loop through all sweeps
        temp_sweep_stop = 0
        while (temp_sweep_stop == 0):
            #determine if there still is a sweep left
            #determine X-start and X end of sweep
            if (self.sweep_x_min_pos + self.sweep_size <= self.sweep_x_max):
                self.sweep_x_max_pos = self.sweep_x_min_pos + self.sweep_size
            else:
                self.sweep_x_max_pos = self.sweep_x_max #set max of image as max pos
                temp_sweep_stop = 1 #mark last loop
            print("Sweep from: " + str(self.sweep_x_min_pos) + ", to: " + str(self.sweep_x_max_pos))
            #Look for Y min and Y max in sweep
            self.sweep_y_min = 0
            self.sweep_y_max = 0
            #get Y min
            temp_break_loop = 0
            for w in range(self.imageconverter.image_array_width):
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    if (self.imageconverter.image_array[h][w] != 0):
                        self.sweep_y_min = w
                        temp_break_loop = 1
                        break
                if (temp_break_loop == 1):
                    break
            #get Y max
            temp_break_loop = 0
            for w in reversed(range(self.imageconverter.image_array_width)):
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    if (self.imageconverter.image_array[h][w] != 0):
                        self.sweep_y_max = w
                        temp_break_loop = 1
                        break
                if (temp_break_loop == 1):
                    break
            print("sweep Y min: " + str(self.sweep_y_min) +", Y max: " + str(self.sweep_y_max))
            #determine printing direction (if necessary)
            self.printing_direction = 1 #only 1 for now
            #Set Y at starting and end position
            if (self.printing_direction == 1):
                self.y_printing_start_pos = self.sweep_y_min * self.pixel_to_pos_multiplier
                self.y_printing_start_pos += self.y_start_pos - self.y_acceleration_distance
                self.y_printing_end_pos = self.sweep_y_max * self.pixel_to_pos_multiplier
                self.y_printing_end_pos += self.y_start_pos + self.y_acceleration_distance
                print("Sweep ranges from: " + str(self.y_printing_start_pos) + "mm, to: " + str(self.y_printing_end_pos) + "mm")
            #set X position
            self.x_printing_pos = self.sweep_x_min_pos * self.pixel_to_pos_multiplier
            self.x_printing_pos += self.x_start_pos
            #fill local print buffer with lines
            print("Filling local buffer with inkjet")
            temp_line_history = ""
            temp_line_string = ""
            temp_line_array = zeros(self.sweep_size)
            temp_line_history = B64.B64ToArray(temp_line_array) #make first history 0
            temp_line_string = temp_line_history #make string also 0
            #add all of starter cap at the front
            if (self.printing_direction == 1):
                temp_pos = ((self.sweep_y_min - 1) * self.pixel_to_pos_multiplier) + self.y_start_pos
                temp_pos *= 1000 #printhead pos is in microns
                temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                self.Binkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                self.Binkjet_lines_left += 1
            for w in range(self.sweep_y_min,self.sweep_y_max):
                #print("Parsing line: " + str(w))
                temp_line_changed = 0 #reset changed
                temp_counter = 0
                for h in range(self.sweep_x_min_pos, self.sweep_x_max_pos):
                    #loop through all pixels to make a new burst
                    temp_line_array[temp_counter] = self.imageconverter.image_array[h][w] #write array value to temp
                    temp_counter += 1
                temp_line_string = B64.B64ToArray(temp_line_array) #convert to string
                if (temp_line_string != temp_line_history):
                    #print("line changed on pos: " + str(w))
                    temp_line_history = temp_line_string
                    #add line to buffer
                    temp_pos = (w * self.pixel_to_pos_multiplier) + self.y_start_pos
                    temp_pos *= 1000 #printhead pos is in microns
                    temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                    self.Binkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                    self.Binkjet_lines_left += 1
            #add all off cap at the end of the image
            temp_line_array = zeros(self.sweep_size)
            temp_line_string = B64.B64ToArray(temp_line_array)
            if (self.printing_direction == 1):
                temp_pos = ((self.sweep_y_max + 1) * self.pixel_to_pos_multiplier) + self.y_start_pos
                temp_pos *= 1000 #printhead pos is in microns
                temp_b64_pos = B64.B64ToSingle(temp_pos) #make position value
                self.Binkjet_line_buffer.append("SBR " + str(temp_b64_pos) + " " + str(temp_line_string))
                self.Binkjet_lines_left += 1
            print("Making printing buffer done: ")
            #print(self.inkjet_line_buffer)
            #wait till the head is idle
            while (self.grbl.motion_state != 'idle'):
                nothing = 0
            print("break from idle, moving to filling buffers")
            #match inkjet and printer pos
            self.BInkjetSetPosition()
            #Fill inkjet buffer with with sweep lines
            print("Filling inkjet buffer")
            #start filling the inkjet buffer on the HP45 lines
            temp_lines_sent = 0
            while(True):
                if (self.Binkjet_lines_left > 0):
                    self.Binkjet.SerialWriteBufferRaw(self.Binkjet_line_buffer[0])
                    #time.sleep(0.001) #this is a good replacement for print, but takes forever
                    print(str(self.Binkjet_line_buffer[0])) #some sort of delay is required, else the function gets filled up too quickly. Will move to different buffer later
                    del self.Binkjet_line_buffer[0] #remove sent line
                    self.Binkjet_lines_left -= 1
                    temp_lines_sent += 1
                else:
                    break
            #send motion lines
            print("Filling motion buffer")
            self.grbl.SerialGotoXY(self.x_printing_pos, self.y_printing_start_pos, self.travel_speed)
            self.grbl.SerialGotoXY(self.x_printing_pos, self.y_printing_end_pos, self.print_speed) 
            self.grbl.StatusIndexSet() #set current status index 
            while (True):
                if (self.grbl.StatusIndexChanged() == 1 and self.grbl.motion_state == 'idle'):
                    print("break conditions for print while loop")
                    break #break if exit conditions met
            self.sweep_x_min_pos += self.sweep_size
        ###end of loop through sweep
        #repeat loop until all sweeps are finished
        print("Printing done")
        #home gantry
        #self.grbl.Home() #home gantry
##############################################################################################################        
#todo
class flow():
    def prot(mfp,zpf,prAll= True):
        lfp = "c*.png"
        if glob.glob(os.path.join(mfp,lfp))==[]:
            print("unziping")
            zip_f = zipfile.ZipFile(mfp+zpf, 'r')
            zip_f.extractall(mfp+"\\")
            zip_f.close()
        """init print"""
        oas = OasisController()
        #oas = OasisController()
        oas.GrblConnect(6)
        #oas.CInkjetConnect()
        #oas.layerHeight = 
        #oas.CInkjetSetDPI()
        #oas.CInkjetSetDensity(temp_density = 0.1)
        #prime
        """ start print """
        if prAll:
            for filename in glob.glob(os.path.join(mfp,lfp)):
                """init layer"""
                fc = filename
                fm = mfp+ "\\m"+filename.split(mfp)[1].split("\\c")[1]
                fy = mfp+ "\\y"+filename.split(mfp)[1].split("\\c")[1]
                fb = mfp+ "\\b"+filename.split(mfp)[1].split("\\c")[1]
                ###do stuff
                """print layer"""
                #oas.OpenFile("file")
                #oas.RunPrintArray()*4
                print(fc)
                print(fm)
                print(fy)
                print(fb)
                """end layer"""
                print("end layer")
        else:
            """init layer"""
            filename = glob.glob(os.path.join(mfp,lfp))[0]
            fc = filename
            fm = mfp+ "\\m"+filename.split(mfp)[1].split("\\c")[1]
            fy = mfp+ "\\y"+filename.split(mfp)[1].split("\\c")[1]
            fb = mfp+ "\\b"+filename.split(mfp)[1].split("\\c")[1]
            ###do stuff
            """print layer"""
            #oas.OpenFile("file")
            #oas.RunPrintArray()*4
            print(fc)
            print(fm)
            print(fy)
            print(fb)
            """end layer"""
            print("end layer")
        #break
        oas.GrblConnect("")
        return()
    
    def cleanup(mfp):
        lfp = "c*.png"
        for filename in glob.glob(os.path.join(mfp,lfp)):
            try:
                os.remove(filename)
                os.remove(mfp+ "\\m"+filename.split(mfp)[1].split("\\c")[1])
                os.remove(mfp+ "\\y"+filename.split(mfp)[1].split("\\c")[1])
                os.remove(mfp+ "\\b"+filename.split(mfp)[1].split("\\c")[1])
            except: 
                PermissionError
            try:
                os.remove(filename)
                os.remove(mfp+ "\\m"+filename.split(mfp)[1].split("\\c")[1])
                os.remove(mfp+ "\\y"+filename.split(mfp)[1].split("\\c")[1])
                os.remove(mfp+ "\\b"+filename.split(mfp)[1].split("\\c")[1])
            except: 
                PermissionError
#main
#"""
class RunPr():
    def runpr():
        dcam = bpy.data.cameras["Camera"]
        r = bpy.data.scenes["Scene"].render
        floco = bpy.data.filepath.split(".blend")[0]
        try:
            os.mkdir(floco)
        except:
            FileExistsError
        #floco = floco+"\\"
        zpf = "\\layers.zip"
        prot(floco,zpf)
        cleanup(floco)
##############################################################################################################
#Function
class cslice():
    def __init__(self):
        super().__init__()
        
    def ren(z,x,ost,obj,thi,cam,mar): #output slices
        print("slicing")
        obj[0].select_set(True)
        bpy.ops.object.duplicate(linked=False)
        dmes = bpy.context.selected_objects
        bpy.context.view_layer.objects.active = dmes[0]
        #"""
        #"""
        cam.location = [0.0,0.0,z]    #move cam to height
        me = cslice.slice(z+ost,x,dmes,thi,mar)    #have a slice of bmesh
        opla = bpy.data.objects.new("Object", me) #new object
        bpy.context.collection.objects.link(opla) 
        print("Done")
        #render
        bpy.context.view_layer.objects.active = opla #make active
        opla.hide_render = True
        obj[0].hide_render = False
        #obj[0].show_in_front = True
        print("rendering")
        try:
            bpy.ops.render.render(use_viewport=True,write_still=True,animation=False) #render
        except:
            print("pls safe file")
        print("Done")
        #obj[0].show_in_front = False
        obj[0].hide_render = False
        opla.hide_render = False
        #clean up    
        opla.select_set(True)
        obj[0].select_set(False)
        bpy.ops.object.delete(use_global=False, confirm=False)
        bpy.context.view_layer.objects.active = obj[0]
        obj[0].select_set(True)
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=False)    
        print("next")
        return()

    def plane(x,z,res): #make plane
        pla = bmesh.new()    
        bmesh.ops.create_grid(pla,x_segments=res,y_segments=res,size=x,calc_uvs= True) #make plne   
        bmesh.ops.translate(pla,vec= (0.0,0.0,z),verts = pla.verts[:]) #move z    
        return(pla)

    def slice(z,x,obj,res,mar): #make slice
        pla = cslice.plane(x,z,res) #get bmesh plane
        me = bpy.data.meshes.new("Mesh")#new mesh
        pla.to_mesh(me)#bmesh to mesh
        opla = bpy.data.objects.new("Object", me)#new obj
        bpy.context.collection.objects.link(opla)
        bpy.context.view_layer.objects.active = opla
        obj[0].select_set(True)
        bpy.ops.object.duplicate(linked=False)
        dmes = bpy.context.selected_objects
        bpy.context.view_layer.objects.active = dmes[0]
        #print(str(dmes))
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.inset( use_relative_offset=True, thickness=0.01, use_individual=True, use_interpolate=True, release_confirm=False)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.editmode_toggle()
        #Boolean and DataTransfure
        print("bool")
        dmes[0].select_set(True)
        dmes[0].modifiers.new(name = "Boolean", type = 'BOOLEAN')
        dmes[0].modifiers.get("Boolean").operation = "INTERSECT"
        dmes[0].modifiers.get("Boolean").object = opla
        dmes[0].modifiers.get("Boolean").solver = "FAST"
        bpy.ops.object.modifier_apply(modifier='Boolean', report=True)
        dmes[0].select_set(False)
        obj[0].select_set(True)
        print("bys")
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.bisect(plane_co=(0.0, 0.0, z), plane_no=(0.0, 0.0, 1))
        bpy.ops.object.editmode_toggle()
        #print("fbys")
        obj[0].select_set(False)
        dmes[0].select_set(True)
        #"""
        print("tri")
        dmes[0].modifiers.new(name = "Triangulate", type = 'TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier='Triangulate', report=True)
        print("sub")
        dmes[0].modifiers.new(name = "SubdivisionSurface", type = 'SUBSURF')
        dmes[0].modifiers.get("SubdivisionSurface").subdivision_type = 'SIMPLE'
        dmes[0].modifiers.get("SubdivisionSurface").levels = 3
        bpy.ops.object.modifier_apply(modifier='SubdivisionSurface', report=True)
        #"""
        print("DT")            
        dmes[0].modifiers.new(name = "DataTransfer", type = 'DATA_TRANSFER')
        dmes[0].modifiers.get("DataTransfer").use_loop_data = True
        dmes[0].modifiers.get("DataTransfer").data_types_loops = {'UV'}
        dmes[0].modifiers.get("DataTransfer").object = obj[0]
        dmes[0].modifiers.get("DataTransfer").loop_mapping = "POLYINTERP_NEAREST"
        dmes[0].modifiers.get("DataTransfer").use_max_distance = True
        dmes[0].modifiers.get("DataTransfer").max_distance = (m.sqrt(((x/res)**2)*2))*mar
        dmes[0].modifiers.get("DataTransfer").mix_mode = "REPLACE"
        bpy.ops.object.modifier_apply(modifier='DataTransfer', report=True)
        #print("adt")
        mes = dmes[0].data           
        bpy.context.view_layer.objects.active = opla
        #clean up    
        dmes[0].select_set(False)
        opla.select_set(True)
        obj[0].select_set(False)
        bpy.ops.object.delete(use_global=False, confirm=False)
        #bpy.context.view_layer.objects.active = obj[0]
        obj[0].select_set(True)
        dmes[0].select_set(True)    
        return(mes)

    def sepcmyk(zpf,mfp):
        lfp = "*.png"
        zip = zipfile.ZipFile(mfp+zpf, "w", zipfile.ZIP_DEFLATED)
        for filename in glob.glob(os.path.join(mfp,lfp)):
            with Image.open(os.path.join(mfp, filename))as image:
                print(filename)
                cmyk_image = image.convert('CMYK')
                try:
                    cim = cmyk_image.getchannel("C")
                    mim = cmyk_image.getchannel("M")
                    yim = cmyk_image.getchannel("Y")
                    kim = cmyk_image.getchannel("K")
                    aim = image.getchannel("A")
                except:
                    ValueError
                #print(mfp+"c"+filename.split(mfp)[1])            
                #break
            cim = ImageMath.eval("convert(max(a, b), 'L')", a=cim, b=kim)
            mim = ImageMath.eval("convert(max(a, b), 'L')", a=mim, b=kim)
            yim = ImageMath.eval("convert(max(a, b), 'L')", a=yim, b=kim)
            aim = ImageMath.eval("a-(c/3)", a=aim, c=cim)
            aim = ImageMath.eval("a-(m/3)", a=aim, m=mim)
            aim = ImageMath.eval("a-(y/3)", a=aim, y=yim)
            cim = cim.convert("1")
            mim = mim.convert("1")
            yim = yim.convert("1")
            aim = aim.convert("1")
            print('c')
            cim.save((mfp+"c"+filename.split(mfp)[1]), format="PNG")
            zip.write((mfp+"c"+filename.split(mfp)[1]), os.path.basename((mfp+"c"+filename.split(mfp)[1])))
            print("m")
            mim.save((mfp+"m"+filename.split(mfp)[1]), format="PNG")
            zip.write((mfp+"m"+filename.split(mfp)[1]), os.path.basename((mfp+"m"+filename.split(mfp)[1])))
            print('y')
            yim.save((mfp+"y"+filename.split(mfp)[1]), format="PNG")
            zip.write((mfp+"y"+filename.split(mfp)[1]), os.path.basename((mfp+"y"+filename.split(mfp)[1])))
            print('b')
            aim.save((mfp+"b"+filename.split(mfp)[1]), format="PNG")
            zip.write((mfp+"b"+filename.split(mfp)[1]), os.path.basename((mfp+"b"+filename.split(mfp)[1])))
            os.remove(filename)
            #break
        zip.close()
        zip.close()
        return()
    #Main------------------------------------------------------------------------------
    #"""
    def slicer(
    zpf = "layers.zip"
    ,j=10001 # layer mameing
    ,layhei = 0.01 #layer thiccccccc in blender units
    ,res = 30 #UV accuritcy, may grately increase slicing time
    ,mar = 2 #margin
    ,ost = -0.0017 #don't touch unless you know what this do in blender units
    ):
        floco = bpy.data.filepath.split(".blend")[0]
        try:
            os.mkdir(floco)
        except:
            FileExistsError
        floco = floco+"\\"
        print(floco)

        #setup
        cam = bpy.data.objects["Camera"] #the cam
        obj = bpy.context.selected_objects
        x = max(
            abs(obj[0].bound_box[0][0]),
            abs(obj[0].bound_box[0][1]),
            abs(obj[0].bound_box[1][0]),
            abs(obj[0].bound_box[1][1]),
            abs(obj[0].bound_box[2][0]),
            abs(obj[0].bound_box[2][1]),
            abs(obj[0].bound_box[3][0]),
            abs(obj[0].bound_box[3][1]),
            abs(obj[0].bound_box[4][0]),
            abs(obj[0].bound_box[4][1]),
            abs(obj[0].bound_box[5][0]),
            abs(obj[0].bound_box[5][1]),
            abs(obj[0].bound_box[6][0]),
            abs(obj[0].bound_box[6][1]),
            abs(obj[0].bound_box[7][0]),
            abs(obj[0].bound_box[7][1])
            )
        z = max(
            obj[0].bound_box[0][2],
            obj[0].bound_box[1][2],
            obj[0].bound_box[2][2],
            obj[0].bound_box[3][2],
            obj[0].bound_box[4][2],
            obj[0].bound_box[5][2],
            obj[0].bound_box[6][2],
            obj[0].bound_box[7][2]
            )
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        print("trianglelate")
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.ops.object.editmode_toggle()
        dcam = bpy.data.cameras["Camera"]
        r = bpy.data.scenes["Scene"].render
        dcam.ortho_scale = x*2+x*0.1
        dcam.clip_start = 0.001
        dcam.clip_end = layhei+0.001
        dcam.type = 'ORTHO'
        r.use_stamp = False
        r.use_compositing = False
        r.image_settings.color_mode = 'RGBA'
        r.image_settings.file_format = 'PNG'
        r.film_transparent = True
        r.use_lock_interface = False
        print("trianglelate")
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.ops.object.editmode_toggle()
        i=0
        x=x*1.2
        while i <=z: #loop for every layer        
            print(round(i, len(str(m.modf(layhei)[0]))-2),"out of",z)
            r.filepath = floco+str(j)
            cslice.ren(i,x,ost,obj,res,cam,mar)
            j=j+1
            i = i+layhei
        r.filepath = floco+str(j)
        cslice.ren(i,x,ost,obj,res,cam,mar)
        cslice.sepcmyk(zpf,floco)
        return()
##############################################################################################################
class priview():
    def ren(z,x,ost,obj,thi,cam,mar): #output slices
        print("slicing")
        obj[0].select_set(True)
        bpy.ops.object.duplicate(linked=False)
        dmes = bpy.context.selected_objects
        bpy.context.view_layer.objects.active = dmes[0]
        priview.slice(z+ost,x,dmes,thi,mar)    #have a slice of bmesh
        return()

    def plane(x,z,res): #make plane
        pla = bmesh.new()    
        bmesh.ops.create_grid(pla,x_segments=res,y_segments=res,size=x,calc_uvs= True) #make plne   
        bmesh.ops.translate(pla,vec= (0.0,0.0,z),verts = pla.verts[:]) #move z    
        return(pla)

    def slice(z,x,obj,res,mar): #make slice
        pla = priview.plane(x,z,res) #get bmesh plane
        me = bpy.data.meshes.new("Mesh")#new mesh
        pla.to_mesh(me)#bmesh to mesh
        opla = bpy.data.objects.new("Object", me)#new obj
        bpy.context.collection.objects.link(opla)
        bpy.context.view_layer.objects.active = opla
        print(opla)        
        #bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
        obj[0].select_set(True)
        bpy.ops.object.duplicate(linked=False)
        dmes = bpy.context.selected_objects
        bpy.context.view_layer.objects.active = dmes[0]
        #print(str(dmes))
        #"""
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.inset( use_relative_offset=True, thickness=0.01, use_individual=True, use_interpolate=True, release_confirm=False)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.editmode_toggle()
        #Boolean and DataTransfure
        #"""
        print("bool")
        dmes[0].select_set(True)
        dmes[0].modifiers.new(name = "Boolean", type = 'BOOLEAN')
        dmes[0].modifiers.get("Boolean").operation = "INTERSECT"
        dmes[0].modifiers.get("Boolean").object = opla
        dmes[0].modifiers.get("Boolean").solver = "FAST"
        #bpy.ops.object.modifier_apply(modifier='Boolean', report=True)
        dmes[0].select_set(False)
        obj[0].select_set(True)
        print("bys")
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.bisect(plane_co=(0.0, 0.0, z), plane_no=(0.0, 0.0, 1))
        bpy.ops.object.editmode_toggle()
        print("fbys")
        obj[0].select_set(False)
        dmes[0].select_set(True)
        #"""
        print("tri")
        dmes[0].modifiers.new(name = "Triangulate", type = 'TRIANGULATE')
        print("sub")
        dmes[0].modifiers.new(name = "SubdivisionSurface", type = 'SUBSURF')
        dmes[0].modifiers.get("SubdivisionSurface").subdivision_type = 'SIMPLE'
        dmes[0].modifiers.get("SubdivisionSurface").levels = 3
        #bpy.ops.object.modifier_apply(modifier='SubdivisionSurface', report=True)
        #"""
        print("DT")            
        dmes[0].modifiers.new(name = "DataTransfer", type = 'DATA_TRANSFER')
        dmes[0].modifiers.get("DataTransfer").use_loop_data = True
        dmes[0].modifiers.get("DataTransfer").data_types_loops = {'UV'}
        dmes[0].modifiers.get("DataTransfer").object = obj[0]
        dmes[0].modifiers.get("DataTransfer").loop_mapping = "POLYINTERP_NEAREST"
        dmes[0].modifiers.get("DataTransfer").use_max_distance = True
        dmes[0].modifiers.get("DataTransfer").max_distance = (m.sqrt(((x/res)**2)*2))*mar
        dmes[0].modifiers.get("DataTransfer").mix_mode = "REPLACE"
        print("adt")
        #bpy.ops.object.modifier_apply(modifier='DataTransfer', report=True)
    #Main------------------------------------------------------------------------------
    #"""
    def slicer(
    zpf = "layers.zip"
    ,j=10001 # layer mameing
    ,layhei = 0.01 #layer thiccccccc in blender units
    ,res = 30 #UV accuritcy, may grately increase slicing time
    ,mar = 2 #margin

    ,ost = -0.0017 #don't touch unless you know what this do in blender units
    ):
        #setup
        obj = bpy.context.selected_objects
        x = max(
            abs(obj[0].bound_box[0][0]),
            abs(obj[0].bound_box[0][1]),
            abs(obj[0].bound_box[1][0]),
            abs(obj[0].bound_box[1][1]),
            abs(obj[0].bound_box[2][0]),
            abs(obj[0].bound_box[2][1]),
            abs(obj[0].bound_box[3][0]),
            abs(obj[0].bound_box[3][1]),
            abs(obj[0].bound_box[4][0]),
            abs(obj[0].bound_box[4][1]),
            abs(obj[0].bound_box[5][0]),
            abs(obj[0].bound_box[5][1]),
            abs(obj[0].bound_box[6][0]),
            abs(obj[0].bound_box[6][1]),
            abs(obj[0].bound_box[7][0]),
            abs(obj[0].bound_box[7][1])
            )
        z = max(
            obj[0].bound_box[0][2],
            obj[0].bound_box[1][2],
            obj[0].bound_box[2][2],
            obj[0].bound_box[3][2],
            obj[0].bound_box[4][2],
            obj[0].bound_box[5][2],
            obj[0].bound_box[6][2],
            obj[0].bound_box[7][2]
            )
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        print("trianglelate")
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.ops.object.editmode_toggle()
        dcam = bpy.data.cameras["Camera"]
        r = bpy.data.scenes["Scene"].render
        dcam.ortho_scale = x*2+x*0.1
        dcam.clip_start = 0.001
        dcam.clip_end = layhei+0.001
        dcam.type = 'ORTHO'
        r.use_stamp = False
        r.use_compositing = False
        r.image_settings.color_mode = 'RGBA'
        r.image_settings.file_format = 'PNG'
        r.film_transparent = True
        r.use_lock_interface = False
        print("trianglelate")
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.ops.object.editmode_toggle()
        i=0
        x=x*1.2
        priview.ren(i,x,ost,obj,res,dcam,mar)
        return()

def register():
    bpy.utils.register_class(FCSlice)
    bpy.utils.register_class(FCPrint)
    bpy.utils.register_class(PreSlice)
    bpy.types.VIEW3D_MT_object.append(menu_func)
    bpy.utils.register_class(LayoutDemoPanel)

def unregister():
    bpy.utils.unregister_class(FCSlice)
    bpy.utils.unregister_class(FCPrint)
    bpy.utils.unregister_class(PreSlice)
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    bpy.utils.unregister_class(LayoutDemoPanel)

if __name__ == "__main__":
    register()
