#!/bin/env python
from __future__ import print_function, division
import sys
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import QtOpenGL
from PyQt4 import uic
from OpenGL import GLU
from OpenGL.GL import *
import OpenGL.GL.shaders as shaders
import os
import time
import math
import numpy as np
import scipy.ndimage as ndimage
from scipy.misc import imread

class MissingComponentError(Exception):
	""" Use this class to express non-critical missing dependency error """
	pass

def load_exr(path):
	try:
		import OpenEXR
		import Imath
	except ImportError:
		raise MissingComponentError()

	f = OpenEXR.InputFile(path)
	chs = f.channels('RGB', Imath.PixelType(Imath.PixelType.FLOAT))
	w = f.header()['dataWindow'].max.x+1
	h = f.header()['dataWindow'].max.y+1

	return np.array([np.fromstring(ch,np.float32).reshape([h,w]) for ch in chs]).transpose([1,2,0])

class CompositeLayerWidget(QtOpenGL.QGLWidget):
	""" A widget that renders final image of a spherical map """
	def __init__(self, parent, layers):
		QtOpenGL.QGLWidget.__init__(self, parent)
		self.parent = parent

		self.yRotDeg = 0.0
		self.layers = layers

		self.t = time.time()

	def initializeGL(self):
		self.qglClearColor(QtGui.QColor(10, 10, 10))
		self.initGeometry()

		glEnable(GL_DEPTH_TEST)

	def resizeGL(self, width, height):
		width = max(width, 1)
		height = max(height, 1)

		glViewport(0, 0, width, height)
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		aspect = width / float(height)

		GLU.gluPerspective(45.0, aspect, 1.0, 100.0)
		glMatrixMode(GL_MODELVIEW)

	def paintGL(self):
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

		glLoadIdentity()
		GLU.gluLookAt(0,0,1, 3*math.cos(self.yRotDeg),3*math.sin(self.yRotDeg),1, 0,0,1)

		glBindTexture(GL_TEXTURE_2D, self.texid)
		glEnableClientState(GL_VERTEX_ARRAY)
		glEnableClientState(GL_COLOR_ARRAY)
		glEnableClientState(GL_TEXTURE_COORD_ARRAY)
		glVertexPointerf(self.sphereVtxArray)
		glColorPointerf(self.sphereClrArray)
		glTexCoordPointerf(self.sphereTexArray)
		glDrawElementsui(GL_QUADS, self.sphereIdxArray)

	def initGeometry(self):
		nlat = 50
		nlon = 50

		# create vertices
		va = []
		ca = []
		ta = []
		for ilat in range(nlat+1):
			lat = math.pi * ilat/nlat
			for ilon in range(nlon+1):
				lon = 2 * math.pi * ilon/nlon

				x = math.sin(lat)*math.cos(lon)
				y = math.sin(lat)*math.sin(lon)
				z = math.cos(lat)

				va.append([x,y,z])
				ca.append([1,1,1])
				ta.append([ilon/nlon, ilat/nlat])

		# create topology
		ia = []
		for ilat in range(nlat):
			for ilon in range(nlon):
				i0 = ilat * nlon + ilon
				i1 = ilat * nlon + ilon+1

				ia.append([i0,i1,i1+nlon,i0+nlon])

		self.sphereVtxArray = 10*np.array(va, np.float32)
		self.sphereClrArray = np.array(ca, np.float32)
		self.sphereTexArray = np.array(ta, np.float32)
		self.sphereIdxArray = np.array(ia, int).flatten()

		vert_shader = shaders.compileShader("""
			#version 400
			layout (location=0) in vec4 position;
			layout (location=1) in vec2 map_position;
			smooth out vec3 f_lix;
			smooth out vec2 f_mposition;

			uniform mat4 trans_model;
			uniform mat4 trans_view;
			uniform mat4 trans_lv; // world pos -> normalized LV index

			void main(){
				vec4 pos_world = trans_model * position;
				vec4 lf_ix = trans_lv * pos_world;

				f_mposition = map_position;
				f_lix = lf_ix.xyz/lf_ix.w;

				gl_Position = trans_view * pos_world;
			}
			""", GL_VERTEX_SHADER)
		frag_shader = shaders.compileShader("""
			#version 400
			smooth in vec3 f_lix;
			smooth in vec2 f_mposition;
			out vec4 outputColor;

			uniform sampler3D lightvolume;
			uniform sampler2D reflectance_map;

			void main(){
		
			}
			""", GL_FRAGMENT_SHADER)


		shader_solid_textured_lf = shaders.compileProgram(vert_shader, frag_shader)
		print(shader_solid_textured_lf)

		# load texture
		glEnable(GL_TEXTURE_2D)
		self.texid = glGenTextures(1)

		#self.load_texture_from('/home/xyx/download/panorama.jpg')


	def load_texture_from(self, path):
		def half(img):
			if img.shape[0]%2==0 and img.shape[1]%2==0 and img.shape[0]>2000:
				img = img.astype(float)
				return (img[::2,::2] + img[1::2,::2] + img[::2,1::2] + img[1::2,1::2])/4
			else:
				return img

		try:
			if os.path.splitext(path)[1].lower() == '.exr':
				tex_pan = load_exr(path)
			else:
				tex_pan = imread(path).astype(float)/255
		except IOError:
			return

		print(tex_pan.shape)

		glBindTexture(GL_TEXTURE_2D, self.texid)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB32F, tex_pan.shape[1], tex_pan.shape[0], 0, GL_RGB, GL_FLOAT, tex_pan.flatten())
		
		glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
		glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
		glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
		glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)

	def tick(self):
		t = time.time()
		dt = t - self.t
		self.t = t

		self.yRotDeg = (self.yRotDeg  + dt*math.radians(30)) % (2*math.pi)
		self.parent.statusBar().showMessage('rotation %f' % self.yRotDeg)

		self.updateGL()

	def updateLayer(self, layers):
		self.load_texture_from(layers.layers[0])

class LayersWidget(QtGui.QListWidget):
	def __init__(self, parent, layers):
		super(LayersWidget, self).__init__(parent)
		self.setAcceptDrops(True)
		self.layers = layers

	def dragEnterEvent(self, event):
		print('ENTER')

		urls = event.mimeData().urls()

		if len(urls)==0:
			# TODO try parsing as URL
			print('text',event.mimeData().text())
			# if fail, reject
			event.ignore()
		else:
			for path_url in urls:
				path = unicode(path_url.toLocalFile())
				if len(path)>0:
					print('local', path)
					self.layers.add_from_path(path)
				else:
					print('URL', path_url.toString())
			event.accept()
		

	def dropEvent(self, event):
		print('DROP')
		print(event.mimeData())
		print(event.mimeData().text())
		print(event.mimeData().urls())
		print(event.mimeData().imageData())

	def updateLayer(self, layers):
		self.clear()
		for item in layers.layers:
			self.addItem(item)


class Layers(QtCore.QObject):
	layerUpdate = QtCore.pyqtSignal(object)

	def __init__(self):
		super(QtCore.QObject, self).__init__()
		self.layers = []

	def add_from_path(self, path):
		self.layers = [path]
		self.layerUpdate.emit(self)

class SphereApplication(QtGui.QApplication):
	def __init__(self, argv):
		QtGui.QApplication.__init__(self,argv)

		# create model
		self.layers = Layers()

		# create view
		self.ui = uic.loadUi('layout.ui')

		# insert composite view
		compositeWidget = CompositeLayerWidget(self.ui, self.layers)

		timer = QtCore.QTimer(self)
		timer.setInterval(20)
		timer.timeout.connect(compositeWidget.tick)
		timer.start()

		self.ui.horizontalLayout.insertWidget(0, compositeWidget,1)

		# insert list view
		listWidget = LayersWidget(self.ui, self.layers)
		self.ui.horizontalLayout.insertWidget(1, listWidget,1)

		self.layers.layerUpdate.connect(compositeWidget.updateLayer)
		self.layers.layerUpdate.connect(listWidget.updateLayer)

		# launch
		self.ui.show()

	def initActions(self):
		self.exitAction = QtGui.QAction('Quit', self)
		self.exitAction.setShortcut('Ctrl+Q')
		self.exitAction.setStatusTip('Exit application')
		self.connect(self.exitAction, QtCore.SIGNAL('triggered()'), self.close)

	def initMenus(self):
		menuBar = self.menuBar()
		fileMenu = menuBar.addMenu('&File')
		fileMenu.addAction(self.exitAction)

	def close(self):
		QtGui.qApp.quit()

if __name__ == '__main__':
	app = SphereApplication(sys.argv)
	sys.exit(app.exec_())
