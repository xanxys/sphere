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
from numpy import array

class GLWidget(QtOpenGL.QGLWidget):
	def __init__(self, parent=None):
		self.parent = parent
		QtOpenGL.QGLWidget.__init__(self, parent)
		self.yRotDeg = 0.0

	def initializeGL(self):
		self.qglClearColor(QtGui.QColor(0, 0,  150))
		self.initGeometry()

		glEnable(GL_DEPTH_TEST)

	def resizeGL(self, width, height):
		if height == 0: height = 1

		glViewport(0, 0, width, height)
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		aspect = width / float(height)

		GLU.gluPerspective(45.0, aspect, 1.0, 100.0)
		glMatrixMode(GL_MODELVIEW)

	def paintGL(self):
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

		glLoadIdentity()
		glTranslate(0.0, 0.0, -50.0)
		glScale(20.0, 20.0, 20.0)
		glRotate(self.yRotDeg, 0.2, 1.0, 0.3)
		glTranslate(-0.5, -0.5, -0.5)

		glEnableClientState(GL_VERTEX_ARRAY)
		glEnableClientState(GL_COLOR_ARRAY)
		glVertexPointerf(self.cubeVtxArray)
		glColorPointerf(self.cubeClrArray)
		glDrawElementsui(GL_QUADS, self.cubeIdxArray)

	def initGeometry(self):
		self.cubeVtxArray = array(
				[[0.0, 0.0, 0.0],
				 [1.0, 0.0, 0.0],
				 [1.0, 1.0, 0.0],
				 [0.0, 1.0, 0.0],
				 [0.0, 0.0, 1.0],
				 [1.0, 0.0, 1.0],
				 [1.0, 1.0, 1.0],
				 [0.0, 1.0, 1.0]])
		self.cubeIdxArray = [
				0, 1, 2, 3,
				3, 2, 6, 7,
				1, 0, 4, 5,
				2, 1, 5, 6,
				0, 3, 7, 4,
				7, 6, 5, 4 ]
		self.cubeClrArray = [
				[0.0, 0.0, 0.0],
				[1.0, 0.0, 0.0],
				[1.0, 1.0, 0.0],
				[0.0, 1.0, 0.0],
				[0.0, 0.0, 1.0],
				[1.0, 0.0, 1.0],
				[1.0, 1.0, 1.0],
				[0.0, 1.0, 1.0 ]]

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

		

	def spin(self):
		self.yRotDeg = (self.yRotDeg  + 1) % 360.0
		self.parent.statusBar().showMessage('rotation %f' % self.yRotDeg)
		self.updateGL()

class LayersWidget(QtGui.QListWidget):
	def __init__(self, parent):
		super(LayersWidget, self).__init__(parent)
		self.setAcceptDrops(True)

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
				else:
					print('URL', path_url.toString())
			event.accept()
		

	def dropEvent(self, event):
		print('DROP')
		print(event.mimeData())
		print(event.mimeData().text())
		print(event.mimeData().urls())
		print(event.mimeData().imageData())

class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		QtGui.QMainWindow.__init__(self)

		self.ui = uic.loadUi('layout.ui')

		# insert GL widget
		glWidget = GLWidget(self)
		glWidget = GLWidget(self)
		self.setCentralWidget(glWidget)

		timer = QtCore.QTimer(self)
		timer.setInterval(20)
		QtCore.QObject.connect(timer, QtCore.SIGNAL('timeout()'), glWidget.spin)
		timer.start()

		self.ui.horizontalLayout.insertWidget(0, glWidget,1)

		# insert layers list
		self.ui.horizontalLayout.insertWidget(1, LayersWidget(self),1)

		# launch
		self.ui.show()

	def dE(self, event):
		print(event)

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
	app = QtGui.QApplication(sys.argv)
	win = MainWindow()
	sys.exit(app.exec_())
