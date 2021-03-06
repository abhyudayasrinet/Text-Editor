import ConfigParser
import gtk
import gobject
import os
import time
import subprocess
import re
import string
import urllib2
import bs4
import thread
import threading
import webbrowser
import gtksourceview2
from htmlparser import *
from autocomplete import *
from pagevals import *
from pygoogle import pygoogle

#TODO
#more languages
#more websites
#better way to fix open close quotes in error message for googling
#background colors/ themes
#function summary pop up
#more preference settings (from createnotebookpage)
#runtime
#run on terminal option
#time to solve


#fixed/added
#file can be opened twice
#reopen last not working
#undo redo shifts view to top
#undo redo not working
#fix autocomplete to check last word till start of line
#ctrl+s not working
#highlight keywords not working for reopen last file

class MainWindow():

	def __init__(self):

		#list of pagevals objects to hold values for each page in the notebook 
		# [scrolledwindow object, labelbox object, filepath, save state, textStates, undoThreadOn, tags]
		self.CodeNotebookPageVals = [] 
		
		#to hold list of keywords to highlight
		self.keywords = [] 

		#dictionary to load/save preferences to
		self.PreferencesDict = {} 

		#index of the previous file to open (needs working)
		self.PreviousFileIndex = 0 

		#used to skip saving text state in case undo was performed(since performing undo will also call the function due to change in text)
		self.UndoPerformed = False 

		self.CtrlPress = False
		# self.loadKeywords()
		self.loadPreferences()
		print(self.PreferencesDict)
		self.init()

	def init(self):

		self.mainWindow = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.mainWindow.set_title("Zar'roc")
		self.mainWindow.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#696969'))
		self.mainWindow.set_position(gtk.WIN_POS_CENTER)
		self.mainWindow.set_default_size(500,500)
		#connect the close button
		self.mainWindow.connect('destroy' , lambda w: gtk.main_quit())
		#set the opacity of the window
		self.mainWindow.set_opacity(self.PreferencesDict["opacity"])
		#perform changes(setting the window separators) to the window when it resizes
		self.mainWindow.connect("configure_event",self.WindowResize)

		self.accel_group = gtk.AccelGroup()
		self.mainWindow.add_accel_group(self.accel_group)

		#main layout to hold child layouts
		self.mainVerticalLayout = gtk.VBox()
		self.mainWindow.add(self.mainVerticalLayout)

		#Create the menu bar
		self.CreateMenuBar()

		#Set hotkeys
		self.SetHotkeys()

		#Create Toolbar
		self.CreateToolBar()

		#Create URL Bar
		self.CreateUrlBar()

		#create the labels for IO
		self.CreateIOLabels()

		#Vertical Pannable Window that holds Input Output text boxes, CodeEditor box and Compiler box
		self.IOCodeWindow = gtk.VPaned()		
		#set the divider
		self.IOCodeWindow.set_position(100)

		#Create input/output text boxes
		self.CreateIOTextBoxes()

		#create the code editor text box
		self.CreateCodeEditorBox()

		#Center Window that contains 1 Vertical paned window and compiler output area
		self.CenterWindow = gtk.VPaned()
		self.mainVerticalLayout.pack_start(self.CenterWindow,padding = 5)
		self.CenterWindow.add(self.IOCodeWindow)

		#set compiler output area
		self.CreateConsoleBox()

		self.mainWindow.show_all()

		gtk.main()

	

	#function called when window is resized
	#used to set the separators of the paned windows
	def WindowResize(self,widget,allocation):

		#adjust pane bar between IO window
		self.IOPanedWindow.set_position(int(allocation.width*0.5))
		#adjust pane bar between IO window and code editor window
		self.IOCodeWindow.set_position(int(allocation.height*0.1))
		#adjust pane bar between IO,codeeditor and compiler output window
		self.CenterWindow.set_position(int(allocation.height*0.75))


	#Creates the compiler output window
	def CreateConsoleBox(self):

		#create a scrolled window for compiler/run output
		self.ConsoleScrolledWindow = gtk.ScrolledWindow()
		self.ConsoleScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.ConsoleText = gtk.TextView()
		self.ConsoleText.set_editable(False) #disable user to edit the content
		self.ConsoleScrolledWindow.add(self.ConsoleText)
		#add to center window(VPaned)
		self.CenterWindow.add(self.ConsoleScrolledWindow)


	def CreateCodeEditorBox(self):

		#Box to hold CodeNotebook
		self.CodeEditorBox = gtk.HBox()

		#code notebook to hold all files as tabs
		self.CodeNotebook = gtk.Notebook() 
		if(self.PreferencesDict["tab_position"] == "TOP"):
			self.CodeNotebook.set_tab_pos(gtk.POS_TOP)
		elif(self.PreferencesDict["tab_position"] == "BOTTOM"):
			self.CodeNotebook.set_tab_pos(gtk.POS_BOTTOM)
		elif(self.PreferencesDict["tab_position"] == "LEFT"):
			self.CodeNotebook.set_tab_pos(gtk.POS_LEFT)
		elif(self.PreferencesDict["tab_position"] == "RIGHT"):
			self.CodeNotebook.set_tab_pos(gtk.POS_RIGHT)
		self.CodeNotebook.set_show_tabs(True)
		self.CodeNotebook.set_show_border(True)
		self.CodeNotebook.set_scrollable(True)
		self.CodeNotebook.show()

		#create and add a notebook page
		page = self.CreateNotebookPage()
		self.CodeNotebookPageVals.append(page)
		self.CodeNotebook.append_page(page.scrolledWindow, page.labelBox)

		#add notebook to box
		self.CodeEditorBox.pack_start(self.CodeNotebook,padding = 5)
		#adding the code editor scrolled window to vertical pannable window
		self.IOCodeWindow.add(self.CodeEditorBox)

		#to highlight keywords in the template
		self.HighlightKeywords()


	#creates a page for the codenotebook
	def CreateNotebookPage(self, file_path = '/Untitled', text = ''):

		#Hbox that makes up the tab label
		labelBox = gtk.HBox()
		pageLabel = gtk.Label(self.GetFileName(file_path)) #tab label
		pageLabel.show()		
		image = gtk.Image() #image of cross button
		image.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
		closeButton = gtk.Button() #close image button
		closeButton.set_image(image) #set the image
		closeButton.set_relief(gtk.RELIEF_NONE) #set the relief of button to none
		closeButton.show()
		labelBox.pack_start(pageLabel)
		labelBox.pack_start(closeButton)
		labelBox.show()
		
		#code editor window (tab content)
		CodeEditorScrolledWindow = gtk.ScrolledWindow()
		CodeEditorScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		#code editor text object
		CodeEditorText = gtksourceview2.View()
		buffer = gtksourceview2.Buffer()
		CodeEditorText.set_buffer(buffer)
		CodeEditorText.set_indent_width(self.PreferencesDict['indent_width'])
		CodeEditorText.set_highlight_current_line(self.PreferencesDict['highlight_current_line'])
		CodeEditorText.set_insert_spaces_instead_of_tabs(self.PreferencesDict['indent_with_spaces'])
		CodeEditorText.set_show_line_numbers(self.PreferencesDict['show_line_numbers'])
		CodeEditorText.set_show_line_marks(self.PreferencesDict['show_line_marks'])
		CodeEditorText.set_auto_indent(True)
		# CodeEditorText.set_show_right_margin(True)
		CodeEditorText.set_smart_home_end(True)
		buffer = CodeEditorText.get_buffer()

		#if text is empty then add the template else add the text
		if(text == ''):
			buffer.set_text(self.PreferencesDict['template'])
		else:
			buffer.set_text(text)


		CodeEditorText.connect('event',self.callback)
		# CodeEditorText.set_buffer(buffer)
		buffer.connect('insert-text',self.HighlightKeywords) #set callback function whenever text is changed
		CodeEditorText.connect('key_press_event',self.CodeEditorKeyPress)
		CodeEditorText.connect('key_release_event',self.CodeEditorKeyRelease)
		# buffer.connect('delete-range',self.TextChangedCodeEditor)
		CodeEditorText.show()
		CodeEditorScrolledWindow.add(CodeEditorText)
		CodeEditorScrolledWindow.show()

		#connect the close button
		closeButton.connect("clicked", self.ClosePage, CodeEditorScrolledWindow)

		#append a list to hold tags of the file
		# self.tags.append([])


		if(file_path == '/Untitled'):
			# create pagevals object  with attributes 
			# [scrolledwindow object, labelbox object, filepath, save state, textStates, undoThreadOn, tags]
			page = PageVals(CodeEditorScrolledWindow, labelBox, None, True, [text], False, 0, [])
			return page
		else:
			print("creating page with path : " + file_path)
			page = PageVals(CodeEditorScrolledWindow, labelBox, file_path, True, [text], False, 0, [])
			return page
	

	def callback(self, widget, event):

		page_num = self.CodeNotebook.get_current_page()
		textview = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0] 
		
		if(event.type == gtk.gdk.KEY_RELEASE and event.keyval == 65507) :
			self.CtrlPress = False
		if(event.type == gtk.gdk.KEY_PRESS and event.keyval == 65507) :
			self.CtrlPress = True
		if(event.type == gtk.gdk.KEY_PRESS and event.keyval == 32 and self.CtrlPress):
			AutoCompleter(textview, self.keywords)


	#handles the insertion of closing braces
	#since the editor automatically adds a closing brace when an opening brace is inserted
	#users generally by intuition add a closing brace too so if a closing brace is being added
	#then just move the cursor by 1 character if a closing brace is already present
	def CodeEditorKeyPress(self,widget,event):

		page_num = self.CodeNotebook.get_current_page()
		buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()

		if(event.string == ')'):
			start = buffer.get_iter_at_offset(buffer.get_property("cursor_position"))
			end = buffer.get_iter_at_offset(buffer.get_property("cursor_position")+1)
			char = buffer.get_text(start,end)
			if(char == ')'):
				iter = buffer.get_iter_at_offset(buffer.get_property("cursor_position")+1)
				buffer.place_cursor(iter)
				return True
		if(event.string == '}'):
			start = buffer.get_iter_at_offset(buffer.get_property("cursor_position"))
			end = buffer.get_iter_at_offset(buffer.get_property("cursor_position")+1)
			char = buffer.get_text(start,end)
			if(char == '}'):
				iter = buffer.get_iter_at_offset(buffer.get_property("cursor_position")+1)
				buffer.place_cursor(iter)
				return True
		if(event.string == ']'):
			start = buffer.get_iter_at_offset(buffer.get_property("cursor_position"))
			end = buffer.get_iter_at_offset(buffer.get_property("cursor_position")+1)
			char = buffer.get_text(start,end)
			if(char == ']'):
				iter = buffer.get_iter_at_offset(buffer.get_property("cursor_position")+1)
				buffer.place_cursor(iter)
				return True
		if(event.string == "'"):
			start = buffer.get_iter_at_offset(buffer.get_property("cursor_position"))
			end = buffer.get_iter_at_offset(buffer.get_property("cursor_position")+1)
			char = buffer.get_text(start,end)
			if(char == "'"):
				iter = buffer.get_iter_at_offset(buffer.get_property("cursor_position")+1)
				buffer.place_cursor(iter)
				return True
			else:
				buffer.insert_at_cursor("'")
				iter = buffer.get_iter_at_offset(buffer.get_property("cursor_position")-1)
				buffer.place_cursor(iter)
		if(event.string == '"'):
			start = buffer.get_iter_at_offset(buffer.get_property("cursor_position"))
			end = buffer.get_iter_at_offset(buffer.get_property("cursor_position")+1)
			char = buffer.get_text(start,end)
			if(char == '"'):
				iter = buffer.get_iter_at_offset(buffer.get_property("cursor_position")+1)
				buffer.place_cursor(iter)
				return True
			else:
				buffer.insert_at_cursor('"')
				iter = buffer.get_iter_at_offset(buffer.get_property("cursor_position")-1)
				buffer.place_cursor(iter)


	#called when a key is pressed into the codeeditor
	def CodeEditorKeyRelease(self, widget, event):
		# page_num = self.CodeNotebook.get_current_page()
		#if the key pressed was backspace or delete or a printable string
		if(event.keyval == 65288 or event.keyval == 65535):
			self.autoCompleteBracketsQuotes(event.string)
			self.TextChangedCodeEditor()

		elif( (event.string in string.printable) and (not event.string == '')) :
			# print(event.string,self.CodeNotebookPageVals[page_num].undoThreadOn)
			self.autoCompleteBracketsQuotes(event.string)
			self.TextChangedCodeEditor()


	#auto adds a closing brace when an opening brace is pressed
	def autoCompleteBracketsQuotes(self, character):
		page_num = self.CodeNotebook.get_current_page()
		buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()
		if(character == '('):
			buffer.insert_at_cursor(')')
			iter = buffer.get_iter_at_offset(buffer.get_property("cursor_position")-1)
			buffer.place_cursor(iter)
		if(character == '['):
			buffer.insert_at_cursor(']')
			iter = buffer.get_iter_at_offset(buffer.get_property("cursor_position")-1)
			buffer.place_cursor(iter)
		if(character == '{'):
			buffer.insert_at_cursor('}')
			iter = buffer.get_iter_at_offset(buffer.get_property("cursor_position")-1)
			buffer.place_cursor(iter)

		
	# Once the thread is over reset the thread state to false to save the state if user types again
	def undoThreadOver(self, page_num):
		self.CodeNotebookPageVals[page_num].undoThreadOn = False
		buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()
		self.CodeNotebookPageVals[page_num].textStates.append(buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
		self.CodeNotebookPageVals[page_num].undoRedoIndex = len(self.CodeNotebookPageVals[page_num].textStates) - 1
		# print("thread over:", self.CodeNotebookPageVals[page_num].textStates)
		# print("undoredoindex:", self.CodeNotebookPageVals[page_num].undoRedoIndex)
		# print("undothreadon:",self.CodeNotebookPageVals[page_num].undoThreadOn)

	#stores the current text state and waits a second to let the user type before storing another state for an undo move
	def undoThread(self,page_num):
		time.sleep(1)
		gobject.idle_add(self.undoThreadOver,page_num)
				

	#called when text is changed in the editor
	def TextChangedCodeEditor(self,arg1 = None, arg2 = None, arg3 = None, arg4 = None):
		page_num = self.CodeNotebook.get_current_page()
		#if undo was done then no need to save text state
		if(not self.UndoPerformed):
			#if the thread is already not running then start it
			if(not self.CodeNotebookPageVals[page_num].undoThreadOn):
				
				buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()
				if(buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()) !=  self.CodeNotebookPageVals[page_num].textStates[-1]):
					del self.CodeNotebookPageVals[page_num].textStates[self.CodeNotebookPageVals[page_num].undoRedoIndex+1:]
					self.CodeNotebookPageVals[page_num].textStates.append(buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
					self.CodeNotebookPageVals[page_num].undoThreadOn = True
					self.CodeNotebookPageVals[page_num].undoRedoIndex = len(self.CodeNotebookPageVals[page_num].textStates) - 1
					# print('starting thread')
					threading.Thread(target = self.undoThread, args = (page_num,) ).start()
				else:
					pass
					# print("buffer text:", buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
					# print("text state :", self.CodeNotebookPageVals[page_num].textStates[-1])
			else:
				# buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()
				# self.CodeNotebookPageVals[page_num].textStates.append(buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter()))
				# print("thread running")
				# print("textstate: ", self.CodeNotebookPageVals[page_num].textStates)
				# print("undoredoindex:", self.CodeNotebookPageVals[page_num].undoRedoIndex)
				pass
		else:
			self.UndoPerformed = False
			# print("passing since undo done")
			pass
			# print(self.CodeNotebookPageVals)
		self.CodeNotebookPageVals[page_num].saveState = False
		self.HighlightKeywords()
		

	#function to go throught the text in the editor box and highlight keywords
	#removes all tags and reapplies them everytime a key is pressed
	#TODO can be improved
	def HighlightKeywords(self, textbuffer = None, iter = None, text = None, length = None):
		# print("highlighting keywords")
		#HIGHLIGHT KEYWORDS BELOW
		page_num = self.CodeNotebook.get_current_page()
		# print("page_num : " + str(page_num))
		#get buffer of page

		buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()

		start_iter = buffer.get_start_iter()
		end_iter = buffer.get_end_iter()

		#remove tags from buffer and tagtable
		try:
			# print("removing existing tags")
			for tag in self.CodeNotebookPageVals[page_num].tags:
				buffer.remove_tag(tag,start_iter,end_iter)
				buffer.get_tag_table().remove(tag)
		except IndexError:
			print("index error on removing tags")
			pass
			# self.tags.append([])

		#set tags list to empty list
		self.CodeNotebookPageVals[page_num].tags = []

		start_iter = buffer.get_start_iter()
		end_iter = buffer.get_end_iter()
		# print(self.keywords)

		#highlight keywords
		for word in self.keywords:

			#search from beginning
			start_iter = buffer.get_start_iter()
			pos = start_iter.forward_search(word,gtk.TEXT_SEARCH_TEXT_ONLY)		
			#if search found
			while(pos != None):
				#check if the word is not a substring but an actual word
				if(pos[1].ends_word() and pos[0].starts_word()):
					self.CodeNotebookPageVals[page_num].tags.append(buffer.create_tag(None,foreground = '#ff0000'))
					buffer.apply_tag(self.CodeNotebookPageVals[page_num].tags[-1], pos[0], pos[1])
				#set iter to end position
				start_iter = pos[1]
				#search again
				pos = start_iter.forward_search(word,gtk.TEXT_SEARCH_TEXT_ONLY)		


	#function to close the respective tab
	def ClosePage(self, widget, child):
		
		#get the index of the page that is being closed
		index = self.CodeNotebook.page_num(child)

		#ask to save if not saved
		if(not self.CodeNotebookPageVals[index].saveState):
			print("save state false open save dialog")
			if(not self.ConfirmSaveDialog(index)):
				return
		else:
			print("file already saved")
			#remove and delete the page
			filepath = self.CodeNotebookPageVals[index].filepath
			print("filepath : " + str(filepath))
			self.CodeNotebook.remove_page(index)
			del self.CodeNotebookPageVals[index]
			if(filepath != None):
				try:
					self.PreferencesDict['recent_files_list'].remove(filepath)
				except ValueError:
					pass
				print("saving as filepath : "+str(filepath))
				self.PreferencesDict['recent_files_list'] = [filepath] + self.PreferencesDict['recent_files_list']
				self.PreferencesDict['recent_files_list'] = self.PreferencesDict['recent_files_list'][0:10]
				self.SavePreferences()
				self.SetRecentFilesMenu()
			self.PreviousFileIndex = 0

	#input output text box codes below
	def CreateIOLabels(self):

		#Labels Bar for Input Output
		self.IOLabelBox = gtk.HBox()
		self.mainVerticalLayout.pack_start(self.IOLabelBox,fill = False, expand = False)
		#Input Label
		self.InputLabel = gtk.Label("Input")
		self.IOLabelBox.pack_start(self.InputLabel)
		#Output Label
		self.OutputLabel = gtk.Label("Output")
		self.IOLabelBox.pack_start(self.OutputLabel)


	def CreateIOTextBoxes(self):

		#Input Output Layout Box
		self.IOBox = gtk.HBox()
		self.IOCodeWindow.add(self.IOBox)

		#Input TextView inside a scrollable window
		self.InputScrolledWindow = gtk.ScrolledWindow()
		self.InputScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.InputText = gtk.TextView()
		self.InputScrolledWindow.add(self.InputText)

		#OutputTextView inside a scrollable window
		self.OutputScrolledWindow = gtk.ScrolledWindow()
		self.OutputScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.OutputText = gtk.TextView()
		self.OutputScrolledWindow.add(self.OutputText)

		#Horizontally Paned Window
		self.IOPanedWindow = gtk.HPaned()
		self.IOPanedWindow.add(self.InputScrolledWindow)
		self.IOPanedWindow.add(self.OutputScrolledWindow)

		#adding the panned window to IOBox
		self.IOBox.pack_start(self.IOPanedWindow,padding = 5)


	#Url bar functions below
	#add the url bar to the window
	def CreateUrlBar(self):

		#TopFrame containing URL bar
		self.UrlBox = gtk.HBox()
		self.mainVerticalLayout.pack_start(self.UrlBox, fill = False, expand = False)
		#URL label
		self.UrlLabel = gtk.Label('URL :')
		self.UrlBox.pack_start(self.UrlLabel, fill = False, expand = False, padding = 5)
		#URL entry box
		self.UrlTextView = gtk.TextView()
		self.UrlTextView.connect('key_release_event',self.urlBarKeyPressed)
		self.UrlTextView.set_events(gtk.gdk.KEY_RELEASE_MASK)
		self.UrlBox.pack_start(self.UrlTextView,padding = 5)

		self.UrlButton = gtk.Button("GO")
		self.UrlButton.connect('clicked',self.urlFetchThread)
		self.UrlBox.pack_start(self.UrlButton,False,False,padding = 5)


	#fetch test cases from url and add to input output boxes
	def getTestCases(self, io):
		print("getting test cases")

		inputbuffer = self.InputText.get_buffer()
		inputbuffer.set_text('')

		outputbuffer = self.OutputText.get_buffer()
		outputbuffer.set_text('')

		inputbuffer.set_text(io[0])
		self.InputText.set_buffer(inputbuffer)
		outputbuffer.set_text(io[1])
		self.OutputText.set_buffer(outputbuffer)


	def urlFetcher(self):
		inputbuffer = self.InputText.get_buffer()
		inputbuffer.set_text('fetching test case...')

		outputbuffer = self.OutputText.get_buffer()
		outputbuffer.set_text('fetching test case...')

		buffer = self.UrlTextView.get_buffer()
		urlVal = buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter())
		io = getInputOutput(urlVal)
		gobject.idle_add(self.getTestCases,io)


	#called when Enter is pressed on the URL bar or Go button is clicked
	def urlFetchThread(self,widget = None,event = None):
		threading.Thread(target = self.urlFetcher, args = () ).start()


	#called when enter is pressed into the URL bar
	def urlBarKeyPressed(self, widget, event):
		if(event.keyval == 65293):
			self.urlFetchThread()


	#MENU BAR FUNCTIONS BELOW
	def CreateMenuBar(self):

		self.CreateFileMenuOption()
		self.CreateEditMenuOption()
		self.CreateViewMenuOption()
		self.CreateToolsMenuOption()

		#create menu bar
		self.MenuBar = gtk.MenuBar()
		self.mainVerticalLayout.pack_start(self.MenuBar, fill = False, expand = False)
		self.MenuBar.show()
		
		#add file options to menu bar		
		self.MenuBar.append(self.FileOption)
		self.MenuBar.append(self.EditOption)
		self.MenuBar.append(self.ViewOption)
		self.MenuBar.append(self.ToolsOption)

	#create tool menu options
	def CreateToolsMenuOption(self):
		self.ToolsMenu = gtk.Menu()
		self.addInputFile = gtk.MenuItem("Add input file..")
		self.addOutputFile = gtk.MenuItem("Add output file..")
		self.setTemplate = gtk.MenuItem("Set template file..")
		#separator = gtk.SeparatorMenuItem()

		self.ToolsMenu.append(self.addInputFile)
		self.ToolsMenu.append(self.addOutputFile)
		self.ToolsMenu.append(self.setTemplate)

		self.addInputFile.connect("activate",self.AddInputFileDialog)
		self.addOutputFile.connect("activate",self.AddOutputFileDialog)
		self.setTemplate.connect("activate",self.SetTemplate)

		self.ToolsMenu.show()
		self.addInputFile.show()
		self.addOutputFile.show()
		self.setTemplate.show()

		self.ToolsOption = gtk.MenuItem("Tools")
		self.ToolsOption.show()
		self.ToolsOption.set_submenu(self.ToolsMenu)


	#Create file menu options
	def CreateFileMenuOption(self):
		
		self.FileMenu = gtk.Menu()
		self.NewEmptyFile = gtk.MenuItem("New")
		self.OpenFile = gtk.MenuItem("Open")
		self.RecentFiles = gtk.MenuItem("Recent Files")
		separator1 = gtk.SeparatorMenuItem()
		self.SaveFile = gtk.MenuItem("Save")
		self.SaveAsFile = gtk.MenuItem("Save As")
		separator2 = gtk.SeparatorMenuItem()
		self.CloseFile = gtk.MenuItem("Close")
		self.Quit = gtk.MenuItem("Quit")
		#append to menu
		self.FileMenu.append(self.NewEmptyFile)
		self.FileMenu.append(self.OpenFile)
		self.FileMenu.append(self.RecentFiles)
		self.FileMenu.append(separator1)
		self.FileMenu.append(self.SaveFile)
		self.FileMenu.append(self.SaveAsFile)
		self.FileMenu.append(separator2)
		self.FileMenu.append(self.CloseFile)
		self.FileMenu.append(self.Quit)
		#connect click functions
		self.NewEmptyFile.connect("activate", self.OpenNewEmptyFile)
		self.OpenFile.connect("activate", self.OpenFileDialog)
		self.CloseFile.connect("activate", self.CloseCurrentPage)
		self.SaveFile.connect("activate", self.SaveFileDialog)
		self.SaveAsFile.connect("activate", self.SaveAsFileDialog)
		self.Quit.connect("activate", self.QuitApp)
		#show options
		self.NewEmptyFile.show()
		self.OpenFile.show()
		self.CloseFile.show()
		self.RecentFiles.show()
		self.SaveFile.show()
		self.SaveAsFile.show()
		self.Quit.show()
		
		#create the reopen last file menu item
		# self.ReopenLastFileItem = gtk.MenuItem("Reopen Last")
		# self.ReopenLastFileItem.connect("activate", self.ReopenLastFile)
		# self.ReopenLastFileItem.show()
		#set the recent files menu
		self.SetRecentFilesMenu()		

		#menu item file
		self.FileOption = gtk.MenuItem("File")
		self.FileOption.show()
		self.FileOption.set_submenu(self.FileMenu)
	

	#creates the recent files menu
	#also called when a tab is closed to refresh recent files list
	def SetRecentFilesMenu(self):
		self.RecentFilesMenu = gtk.Menu()
		self.ReopenLastFileItem = gtk.MenuItem("Reopen Last File")
		self.ReopenLastFileItem.connect("activate", self.ReopenLastFile)
		try:
			self.ReopenLastFileItem.add_accelerator("activate", self.accel_group, ord('T'), gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK, gtk.ACCEL_VISIBLE) 
		except AttributeError:
			pass
		self.ReopenLastFileItem.show()
		self.RecentFilesMenu.append(self.ReopenLastFileItem)
		# self.ReopenLastFileItem.show()

		separator = gtk.SeparatorMenuItem()
		self.RecentFilesMenu.append(separator)
		# print("recent_files_list", self.PreferencesDict['recent_files_list'])
		for tempFile in self.PreferencesDict['recent_files_list']:
			fileItem = gtk.MenuItem(tempFile)
			self.RecentFilesMenu.append(fileItem)
			fileItem.connect("activate",self.OpenRecentFile, tempFile)
			fileItem.show()
		self.RecentFiles.set_submenu(self.RecentFilesMenu)


	#Create Edit Menu
	def CreateEditMenuOption(self):

		self.EditMenu = gtk.Menu()
		self.Undo = gtk.MenuItem("Undo")
		self.Redo = gtk.MenuItem("Redo")
		separator1 = gtk.SeparatorMenuItem()
		self.Cut = gtk.MenuItem("Cut")
		self.Copy = gtk.MenuItem("Copy")
		self.Paste = gtk.MenuItem("Paste")
		separator2 = gtk.SeparatorMenuItem()
		self.Preferences = gtk.MenuItem("Preferences")
		self.EditMenu.append(self.Undo)
		self.EditMenu.append(self.Redo)
		self.EditMenu.append(separator1)
		self.EditMenu.append(self.Cut)
		self.EditMenu.append(self.Copy)
		self.EditMenu.append(self.Paste)
		self.EditMenu.append(separator2)
		self.EditMenu.append(self.Preferences)
		self.Undo.connect("activate",self.UndoText)
		self.Redo.connect("activate",self.RedoText)
		self.Cut.connect("activate",self.CutText)
		self.Copy.connect("activate",self.CopyText)
		self.Paste.connect("activate",self.PasteText)
		self.Preferences.connect("activate",self.OpenPreferences)
		self.Cut.show()
		self.Preferences.show()

		#menu edit item
		self.EditOption = gtk.MenuItem("Edit")
		self.EditOption.show()
		self.EditOption.set_submenu(self.EditMenu)


	def CreateViewMenuOption(self):

		self.ViewMenu = gtk.Menu()
		#show input outbox check item
		self.ShowInputOutputPane = gtk.CheckMenuItem("Show Input/Output Window")
		self.ShowInputOutputPane.set_active(True)
		self.ShowInputOutputPane.connect("toggled",self.ToggleInputOutputWindow)
		self.ViewMenu.append(self.ShowInputOutputPane)
		self.ShowInputOutputPane.show()

		#show console check item
		self.ShowConsoleWindow  = gtk.CheckMenuItem("Show Console Window")
		self.ShowConsoleWindow.set_active(True)
		self.ShowConsoleWindow.connect("toggled",self.ToggleConsoleWindow)
		self.ViewMenu.append(self.ShowConsoleWindow)
		self.ShowConsoleWindow.show()

		#show url bar
		self.ShowUrlBar  = gtk.CheckMenuItem("Show Url Bar")
		self.ShowUrlBar.set_active(True)
		self.ShowUrlBar.connect("toggled",self.ToggleUrlBar)
		self.ViewMenu.append(self.ShowUrlBar)
		self.ShowUrlBar.show()

		self.ViewOption = gtk.MenuItem("View")
		self.ViewOption.show()
		self.ViewOption.set_submenu(self.ViewMenu)


	#reopen the previous file (hotkey function)
	def ReopenLastFile(self, widget):
		
		print("Previous files : ")
		print(self.PreferencesDict['recent_files_list'])
		try:
			filepath = self.PreferencesDict['recent_files_list'][self.PreviousFileIndex]

			#check if the file is already not open
			#if it is then bring that file to focus
			#else open it
			flag = 0
			index = 0
			for page in self.CodeNotebookPageVals:
				if(page.filepath == filepath):
					flag = 1
					break
				index += 1

			if(flag):
				print("file already open")
				self.CodeNotebook.set_current_page(index)
				self.PreviousFileIndex += 1 
				return

			print("reopening file with path : " + filepath)
		except:
			print("reopen previous files error")
			return
		self.OpenRecentFile(None, filepath)
		self.PreviousFileIndex += 1


	#show hide url bar
	def ToggleUrlBar(self, widget):

		if(self.ShowUrlBar.get_active()):
			self.UrlBox.show()
		else:
			self.UrlBox.hide()


	#show hide console window
	def ToggleConsoleWindow(self, widget):

		if(self.ShowConsoleWindow.get_active()):
			self.ConsoleScrolledWindow.show()
		else:
			self.ConsoleScrolledWindow.hide()
		

	#show hide input output pane/window
	def ToggleInputOutputWindow(self, widget):

		if(self.ShowInputOutputPane.get_active()):
			self.IOLabelBox.show()
			self.IOBox.show()
		else:
			self.IOLabelBox.hide()
			self.IOBox.hide()


	#opens the recent file
	def OpenRecentFile(self,widget,filepath):

		#check if the file is already not open
		#if it is then bring that file to focus
		#else open it
		flag = 0
		index = 0
		for page in self.CodeNotebookPageVals:
			if(page.filepath == filepath):
				flag = 1
				break
			index += 1

		if(flag):
			print("file already open")
			self.CodeNotebook.set_current_page(index)
			self.PreviousFileIndex += 1 
			return

		f = open(filepath)
		text = f.read()
		f.close()
		page = self.CreateNotebookPage(filepath, text)
		self.CodeNotebookPageVals.append(page)
		self.CodeNotebook.append_page(page.scrolledWindow, page.labelBox)		
		self.CodeNotebook.set_current_page(-1)
		print("going to highlight")
		self.loadKeywords()
		self.HighlightKeywords()


	#close the current page
	def CloseCurrentPage(self, widget):
		# print('close current page')
		index = self.CodeNotebook.get_current_page()
		if(not self.CodeNotebookPageVals[index].saveState):
			# print("save state false open save dialog")
			if(not self.ConfirmSaveDialog(index)):
				return
		else:
			# print("save state true open save dialog")
			filepath = self.CodeNotebookPageVals[index].filepath
			# print("filepath : " + str(filepath))
			self.CodeNotebook.remove_page(index)
			del self.CodeNotebookPageVals[index]
			if(filepath != None):
				try:
					self.PreferencesDict['recent_files_list'].remove(filepath)
				except ValueError:
					pass
				
				# print(self.PreferencesDict['recent_files_list'])
				
				if(self.PreferencesDict['recent_files_list'].__contains__(filepath)):
					index = self.PreferencesDict['recent_files_list'].index(filepath)
					del self.PreferencesDict['recent_files_list'][index]

				self.PreferencesDict['recent_files_list'] = [filepath] + self.PreferencesDict['recent_files_list']
				self.PreferencesDict['recent_files_list'] = self.PreferencesDict['recent_files_list'][0:10]
				
				# print(self.PreferencesDict['recent_files_list'])
				
				self.SavePreferences()
				self.SetRecentFilesMenu()
			self.PreviousFileIndex = 0


	#function to undo text
	def UndoText(self,widget):

		#get page number
		page_num = self.CodeNotebook.get_current_page()
		#get buffer
		buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()
		#perform undo
		buffer.undo()
		#highlight keywords
		self.HighlightKeywords()
		return

	#function to redo text
	def RedoText(self, widget):

		#get the page number
		page_num = self.CodeNotebook.get_current_page()
		#get buffer
		buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()
		#perform redo
		buffer.redo()
		#highlight keywords
		self.HighlightKeywords()
		return


	#function to paste text into the editor from clipboard
	def PasteText(self,widget):
		print("pasting text")
		child = self.mainWindow.get_focus()
		#don't allow pasting in the console output box
		if(child == self.ConsoleText):
			return
		buffer = child.get_buffer()
		clipboard =  gtk.Clipboard()
		text = clipboard.wait_for_text()
		#deleted any selected text
		buffer.delete_selection(True,True)
		#paste copied text
		buffer.insert_at_cursor(text)
		self.HighlightKeywords()
		#return True

	#function to copy selected text onto the clipboard
	def CopyText(self,widget):
		child = self.mainWindow.get_focus()
		buffer = child.get_buffer()
		clipboard =  gtk.Clipboard()
		buffer.copy_clipboard(clipboard)

	#function to cut selected text onto the clipboard
	def CutText(self,widget):
		child = self.mainWindow.get_focus()
		#don't allow cutting in the console output box
		if(child == self.ConsoleText):
			return
		buffer = child.get_buffer()
		clipboard = gtk.Clipboard()
		buffer.cut_clipboard(clipboard,True)
		self.HighlightKeywords()

	#Response on clicking preferences in edit menu
	def OpenPreferences(self, widget):

		#create dialog
		self.PreferencesDialog = gtk.Dialog("Preferences")
		self.PreferencesDialog.set_has_separator(True)
		
		table = gtk.Table(rows = 4, columns = 2)
		self.PreferencesDialog.vbox.pack_start(table)

		#set opacity entry
		label = gtk.Label("Opacity (0-1) ")
		label.set_alignment(0,0)
		table.attach(label,0,1,0,1)
		self.PreferencesOpacityEntry = gtk.Entry()
		self.PreferencesOpacityEntry.set_text(str(self.PreferencesDict['opacity']))
		self.PreferencesOpacityEntry.connect('changed', self.checkOpacityEntry) #connect to function to validate values
		table.attach(self.PreferencesOpacityEntry,1,2,0,1)
		
		#create radio buttons for tab position
		label = gtk.Label("Tab Position ")
		label.set_alignment(0,0)
		table.attach(label,0,1,1,2)
		vbox = gtk.VBox()
		tabsTopRadio = gtk.RadioButton(None,"Top")
		tabsTopRadio.connect("toggled",self.changeCodeNotebookTabPosition,"TOP")
		#set to marked if set by user
		if(self.PreferencesDict["tab_position"] == "TOP"):
			tabsTopRadio.set_active(True)
		tabsTopRadio.show()
		vbox.pack_start(tabsTopRadio)

		tabsLeftRadio = gtk.RadioButton(tabsTopRadio,"Left")
		tabsLeftRadio.connect("toggled",self.changeCodeNotebookTabPosition,"LEFT")
		if(self.PreferencesDict["tab_position"] == "LEFT"):
			tabsLeftRadio.set_active(True)
		tabsLeftRadio.show()
		vbox.pack_start(tabsLeftRadio)

		tabsRightRadio = gtk.RadioButton(tabsTopRadio,"Right")
		tabsRightRadio.connect("toggled",self.changeCodeNotebookTabPosition,"RIGHT")
		if(self.PreferencesDict["tab_position"] == "RIGHT"):
			tabsRightRadio.set_active(True)
		tabsRightRadio.show()
		vbox.pack_start(tabsRightRadio)
		
		tabsBottomRadio = gtk.RadioButton(tabsTopRadio,"Bottom")
		tabsBottomRadio.connect("toggled",self.changeCodeNotebookTabPosition,"BOTTOM")
		if(self.PreferencesDict["tab_position"] == "BOTTOM"):
			tabsBottomRadio.set_active(True)
		tabsBottomRadio.show()
		vbox.pack_start(tabsBottomRadio)
		table.attach(vbox,1,2,1,2)



		#radio buttons for indent width options
		label = gtk.Label("Indent width ")
		label.set_alignment(0,0)
		table.attach(label,0,1,2,3)

		vbox = gtk.VBox()
		indentWidth2Radio = gtk.RadioButton(None,"2")
		indentWidth2Radio.set_alignment(0,0)
		indentWidth2Radio.connect("toggled",self.ChangeIndentWidth,2)
		if(self.PreferencesDict["indent_width"] == 2):
			indentWidth2Radio.set_active(True)
		indentWidth2Radio.show()
		vbox.pack_start(indentWidth2Radio)

		indentWidth4Radio = gtk.RadioButton(indentWidth2Radio,"4")
		indentWidth4Radio.connect("toggled",self.ChangeIndentWidth,4)
		if(self.PreferencesDict["indent_width"] == 4):
			indentWidth4Radio.set_active(True)
		indentWidth4Radio.show()
		vbox.pack_start(indentWidth4Radio)

		indentWidth8Radio = gtk.RadioButton(indentWidth2Radio,"8")
		indentWidth8Radio.connect("toggled",self.ChangeIndentWidth,8)
		if(self.PreferencesDict["indent_width"] == 8):
			indentWidth8Radio.set_active(True)
		indentWidth8Radio.show()
		vbox.pack_start(indentWidth8Radio)
		table.attach(vbox,1,2,2,3)


		#use spaces to indent option
		label = gtk.Label("Use spaces to indent ")
		label.set_alignment(0,0)
		table.attach(label,0,1,3,4)
		checkbutton = gtk.CheckButton()
		checkbutton.set_alignment(0,0)
		checkbutton.connect("toggled",self.ToggleIndentWithSpaces)
		if(self.PreferencesDict['indent_with_spaces'] == True):
			checkbutton.set_active(True)
		else:
			checkbutton.set_active(False)
		table.attach(checkbutton,1,2,3,4)

		#show line numbers option
		label = gtk.Label("Show line numbers ")
		label.set_alignment(0,0)
		table.attach(label,0,1,4,5)
		checkbutton = gtk.CheckButton()
		checkbutton.set_alignment(0,0)
		checkbutton.connect("toggled",self.ShowLineNumbers)
		if(self.PreferencesDict['show_line_numbers'] == True):
			checkbutton.set_active(True)
		else:
			checkbutton.set_active(False)
		table.attach(checkbutton,1,2,4,5)

		#highlight current line option
		label = gtk.Label("Highlight current line ")
		label.set_alignment(0,0)
		table.attach(label,0,1,5,6)
		checkbutton = gtk.CheckButton()
		checkbutton.set_alignment(0,0)
		checkbutton.connect("toggled",self.HighlightCurrentLine)
		if(self.PreferencesDict['highlight_current_line'] == True):
			checkbutton.set_active(True)
		else:
			checkbutton.set_active(False)
		table.attach(checkbutton,1,2,5,6)

		#show line mark option
		label = gtk.Label("Show line marks ")
		label.set_alignment(0,0)
		table.attach(label,0,1,6,7)
		checkbutton = gtk.CheckButton()
		checkbutton.set_alignment(0,0)
		checkbutton.connect("toggled",self.ShowLineMarks)
		if(self.PreferencesDict['show_line_marks'] == True):
			checkbutton.set_active(True)
		else:
			checkbutton.set_active(False)
		table.attach(checkbutton,1,2,6,7)


		table.show_all()

		#add cancel button
		button = self.PreferencesDialog.add_button("Close",gtk.RESPONSE_ACCEPT)
		button.connect("clicked",self.ClosePreferences) #close the box on clicking cancel
		button.show()

		self.PreferencesDialog.run()
		self.PreferencesDialog.destroy()	


	#called when highling current line option is toggled
	def ShowLineMarks(self,widget):
		if(widget.get_active()):
			self.PreferencesDict['show_line_marks'] = True
			for i in range(0,len(self.CodeNotebookPageVals)):
				self.CodeNotebookPageVals[i].scrolledWindow.get_children()[0].set_show_line_marks(True)
		else:
			self.PreferencesDict['show_line_marks'] = False
			for i in range(0,len(self.CodeNotebookPageVals)):
				self.CodeNotebookPageVals[i].scrolledWindow.get_children()[0].set_show_line_marks(False)
		self.SavePreferences()


	#called when highling current line option is toggled
	def HighlightCurrentLine(self,widget):
		if(widget.get_active()):
			self.PreferencesDict['highlight_current_line'] = True
			for i in range(0,len(self.CodeNotebookPageVals)):
				self.CodeNotebookPageVals[i].scrolledWindow.get_children()[0].set_highlight_current_line(True)
		else:
			self.PreferencesDict['highlight_current_line'] = False
			for i in range(0,len(self.CodeNotebookPageVals)):
				self.CodeNotebookPageVals[i].scrolledWindow.get_children()[0].set_highlight_current_line(False)
		self.SavePreferences()


	#called when show line numbers option is toggled
	def ShowLineNumbers(self,widget):
		if(widget.get_active()):
			self.PreferencesDict['show_line_numbers'] = True
			for i in range(0,len(self.CodeNotebookPageVals)):
				self.CodeNotebookPageVals[i].scrolledWindow.get_children()[0].set_show_line_numbers(True)
		else:
			self.PreferencesDict['show_line_numbers'] = False
			for i in range(0,len(self.CodeNotebookPageVals)):
				self.CodeNotebookPageVals[i].scrolledWindow.get_children()[0].set_show_line_numbers(False)
		self.SavePreferences()


	#called when user toggles the use spaces to indent checkbutton
	def ToggleIndentWithSpaces(self,widget):

		if(widget.get_active()):
			self.PreferencesDict['indent_with_spaces'] = True
			for i in range(0,len(self.CodeNotebookPageVals)):
				self.CodeNotebookPageVals[i].scrolledWindow.get_children()[0].set_insert_spaces_instead_of_tabs(True)
			# print("insert spaces true")
		else:
			self.PreferencesDict['indent_with_spaces'] = False
			for i in range(0,len(self.CodeNotebookPageVals)):
				self.CodeNotebookPageVals[i].scrolledWindow.get_children()[0].set_insert_spaces_instead_of_tabs(False)
			# print("insert spaces false")
		self.SavePreferences()


	#called when indent width is changed in preferences
	def ChangeIndentWidth(self,widget,val):		

		for i in range(0,len(self.CodeNotebookPageVals)):
			self.CodeNotebookPageVals[i].scrolledWindow.get_children()[0].set_indent_width(val)
		self.PreferencesDict["indent_width"] = val
		self.SavePreferences()

	#changes the position of the tab to the value of option
	def changeCodeNotebookTabPosition(self,widget,option):

		if(option == "BOTTOM"):
			self.CodeNotebook.set_tab_pos(gtk.POS_BOTTOM)
			self.PreferencesDict["tab_position"] = "BOTTOM"
		elif(option == "TOP"):
			self.CodeNotebook.set_tab_pos(gtk.POS_TOP)
			self.PreferencesDict["tab_position"] = "TOP"
		elif(option == "RIGHT"):
			self.CodeNotebook.set_tab_pos(gtk.POS_RIGHT)
			self.PreferencesDict["tab_position"] = "RIGHT"
		elif(option == "LEFT"):
			self.CodeNotebook.set_tab_pos(gtk.POS_LEFT)
			self.PreferencesDict["tab_position"] = "LEFT"
		self.SavePreferences();

	#check if value inside entry box is numeric
	def checkOpacityEntry(self, widget):

		try:
			val = float(self.PreferencesOpacityEntry.get_text())
			if(val<0):
				self.PreferencesOpacityEntry.set_text('0')
			elif(val>1):
				self.PreferencesOpacityEntry.set_text('1')
		except ValueError:
			self.PreferencesOpacityEntry.set_text('')
		try:
			val = float(self.PreferencesOpacityEntry.get_text())
		except ValueError:
			val = 1
		self.mainWindow.set_opacity(val)
		self.PreferencesDict["opacity"] = val
		self.SavePreferences()

	#write preferences to preferences file
	def SavePreferences(self):

		config = ConfigParser.RawConfigParser()
		config.add_section('Section1')
		config.set('Section1','opacity',self.PreferencesDict['opacity'])
		config.set('Section1','tab_position',self.PreferencesDict['tab_position'])
		config.set('Section1','recent_files_list',self.PreferencesDict['recent_files_list'])
		config.set('Section1','template',self.PreferencesDict['template'])
		config.set('Section1','indent_width',self.PreferencesDict['indent_width'])
		config.set('Section1','indent_with_spaces',self.PreferencesDict['indent_with_spaces'])
		config.set('Section1','show_line_numbers',self.PreferencesDict['show_line_numbers'])
		config.set('Section1','highlight_current_line',self.PreferencesDict['highlight_current_line'])
		config.set('Section1','show_line_marks',self.PreferencesDict['show_line_marks'])
		with open('preferences.cfg', 'w') as configfile:
			config.write(configfile)

	#load the stored preferences
	def loadPreferences(self):

		config = ConfigParser.RawConfigParser()
		config.read('preferences.cfg')
		try:
			self.PreferencesDict["opacity"] = eval(config.get('Section1', 'opacity'))
		except:
			self.PreferencesDict["opacity"] = 1
		try:
			self.PreferencesDict["tab_position"] = config.get('Section1', 'tab_position')
		except:
			self.PreferencesDict["tab_position"] = "TOP"
		try:
			self.PreferencesDict["recent_files_list"] = eval(config.get('Section1','recent_files_list'))
		except:
			self.PreferencesDict["recent_files_list"] = []
		try:
			self.PreferencesDict["template"] = config.get('Section1','template')
		except:
			self.PreferencesDict["template"] = ''
		try:
			self.PreferencesDict["indent_width"] = eval(config.get('Section1','indent_width'))
		except:
			self.PreferencesDict["indent_width"] = 4
		try:
			self.PreferencesDict["indent_with_spaces"] = eval(config.get('Section1','indent_with_spaces'))
		except:
			self.PreferencesDict["indent_with_spaces"] = False
		try:
			self.PreferencesDict["show_line_numbers"] = eval(config.get('Section1','show_line_numbers'))
		except:
			self.PreferencesDict["show_line_numbers"] = True
		try:
			self.PreferencesDict["highlight_current_line"] = eval(config.get('Section1','highlight_current_line'))
		except:
			self.PreferencesDict["highlight_current_line"] = True
		try:
			self.PreferencesDict["show_line_marks"] = eval(config.get('Section1','show_line_marks'))
		except:
			self.PreferencesDict["show_line_marks"] = True

	#close the dialog box
	def ClosePreferences(self,widget):

		self.PreferencesDialog.destroy()


	#add input test cases file
	#reads input test cases from the file
	def AddInputFileDialog(self,widget):
		dialog = gtk.FileChooserDialog("Open..", None, gtk.FILE_CHOOSER_ACTION_OPEN, 
											(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		response = dialog.run()
		if response == gtk.RESPONSE_OK:

			filestream = open(dialog.get_filename()) #open stream to read file
			filepath = dialog.get_filename() #extract filename
			text = filestream.read() #extract text from file stream
			filestream.close() #close stream

			inputbuffer = self.InputText.get_buffer()
			inputbuffer.set_text('')

			inputbuffer.set_text(text)
			self.InputText.set_buffer(inputbuffer)
		dialog.destroy()


	#add output test cases file
	#reads output test cases from the file
	def AddOutputFileDialog(self, widget):

		dialog = gtk.FileChooserDialog("Open..", None, gtk.FILE_CHOOSER_ACTION_OPEN, 
											(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		response = dialog.run()
		if response == gtk.RESPONSE_OK:

			filestream = open(dialog.get_filename()) #open stream to read file
			filepath = dialog.get_filename() #extract filename
			text = filestream.read() #extract text from file stream
			filestream.close() #close stream


			outputbuffer = self.OutputText.get_buffer()
			outputbuffer.set_text('')

			outputbuffer.set_text(text)
			self.OutputText.set_buffer(outputbuffer)
		dialog.destroy()
		

	#defines the template to be imported into every new file created
	def SetTemplate(self,widget):
		self.templateWindow = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.templateWindow.set_title("Set Template")
		self.templateWindow.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#696969'))
		self.templateWindow.set_position(gtk.WIN_POS_CENTER)
		self.templateWindow.set_default_size(500,500)

		vbox = gtk.VBox()
		self.templateWindow.add(vbox)

		self.templateTextview = gtk.TextView()
		text = self.PreferencesDict['template']
		buffer = self.templateTextview.get_buffer()
		buffer.set_text(text)
		vbox.pack_start(self.templateTextview)

		hbox = gtk.HBox()
		vbox.pack_start(hbox,fill=False,expand=False)

		saveButton = gtk.Button("Save")
		saveButton.connect("clicked",self.SaveTemplate)

		hbox.pack_start(saveButton)

		self.templateWindow.show_all()


	def SaveTemplate(self,widget):

		buffer = self.templateTextview.get_buffer()
		text = buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter())
		self.PreferencesDict['template'] = str(text)
		self.SavePreferences()
		self.templateWindow.destroy()


	#open an empty file and append it to the end of the notebook tabs
	def OpenNewEmptyFile(self,widget):

		page = self.CreateNotebookPage()
		self.CodeNotebook.append_page(page.scrolledWindow,page.labelBox)
		self.CodeNotebookPageVals.append(page)
		self.CodeNotebook.set_current_page(-1)
		self.HighlightKeywords()


	#show pop up dialog if changes made to file have not been saved and the user is quitting
	def ConfirmSaveDialog(self, index):
		print("confirmsavedialog")
		dialogWindow = gtk.Dialog("Preferences", None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
										 (gtk.STOCK_NO, gtk.RESPONSE_NO, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
		dialogWindow.set_has_separator(True)
		dialogWindow.set_default_response(gtk.RESPONSE_YES)
		hbox = gtk.HBox()
		label = gtk.Label("Save before Quitting?")
		label.show()
		hbox.show()
		hbox.pack_start(label)
		dialogWindow.vbox.pack_start(hbox, padding = 5)

		response = dialogWindow.run()

		if(response == gtk.RESPONSE_NO):
			print("close without save")
			filepath = self.CodeNotebookPageVals[index].filepath
			self.CodeNotebook.remove_page(index)
			del self.CodeNotebookPageVals[index]
			if(filepath != None):
				try:
					self.PreferencesDict['recent_files_list'].remove(filepath)
				except ValueError:
					pass

				if(self.PreferencesDict['recent_files_list'].__contains__(filepath)):
					index = self.PreferencesDict['recent_files_list'].index(filepath)
					del self.PreferencesDict['recent_files_list'][index]

				self.PreferencesDict['recent_files_list'] = [filepath] + self.PreferencesDict['recent_files_list']
				self.PreferencesDict['recent_files_list'] = self.PreferencesDict['recent_files_list'][0:10]
				self.SavePreferences()
				self.SetRecentFilesMenu()
			self.PreviousFileIndex = 0
			dialogWindow.destroy()
		elif(response == gtk.RESPONSE_CANCEL):
			print("Dont close")
			dialogWindow.destroy()
		elif(response == gtk.RESPONSE_OK):
			print("save file")
			# self.SaveFileDialog(None, page_num = index)
			filepath = self.CodeNotebookPageVals[index].filepath
			self.CodeNotebook.remove_page(index)
			del self.CodeNotebookPageVals[index]
			# del self.tags[index]
			# print("wtf")
			if(filepath != None):
				try:
					self.PreferencesDict['recent_files_list'].remove(filepath)
				except ValueError:
					pass

				if(self.PreferencesDict['recent_files_list'].__contains__(filepath)):
					index = self.PreferencesDict['recent_files_list'].index(filepath)
					del self.PreferencesDict['recent_files_list'][index]

				self.PreferencesDict['recent_files_list'] = [filepath] + self.PreferencesDict['recent_files_list']
				self.PreferencesDict['recent_files_list'] = self.PreferencesDict['recent_files_list'][0:10]
				self.SavePreferences()
				self.SetRecentFilesMenu()
			self.PreviousFileIndex = 0
			dialogWindow.destroy()


	#create the open file dialog and open the selected file in a new tab if any
	def OpenFileDialog(self, widget):
		print("openfiledialog")
		dialog = gtk.FileChooserDialog("Open..", None, gtk.FILE_CHOOSER_ACTION_OPEN, 
											(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		response = dialog.run()
		if response == gtk.RESPONSE_OK:

			filestream = open(dialog.get_filename()) #open stream to read file
			filepath = dialog.get_filename() #extract filename

			#check if the file is already not open
			#if it is then bring that file to focus
			#else open it
			flag = 0
			index = 0
			for page in self.CodeNotebookPageVals:
				if(page.filepath == filepath):
					flag = 1
					break
				index += 1

			if(flag):
				print("file already open")
				dialog.destroy()
				self.CodeNotebook.set_current_page(index)
				return

			text = filestream.read() #extract text from file stream
			filestream.close() #close stream

			#create the page and add the text to the page
			page = self.CreateNotebookPage(filepath, text)
			page.printFilePath()

			#append page details to notebook list
			self.CodeNotebookPageVals.append(page)
			#append the page into the code notebook(set of tabs)
			self.CodeNotebook.append_page(page.scrolledWindow, page.labelBox)		

		elif response == gtk.RESPONSE_CANCEL:
			print('Closed, no files selected') #log

		dialog.destroy()
		self.CodeNotebook.set_current_page(-1)
		self.loadKeywords()
		self.HighlightKeywords()


	#open the save as file dialog and save the file 
	def SaveAsFileDialog(self, widget):
		print("saveasfiledialog")
		dialog = gtk.FileChooserDialog("Save As..", None, gtk.FILE_CHOOSER_ACTION_SAVE,
											(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		response = dialog.run()
		if response == gtk.RESPONSE_OK:

		    filestream = open(dialog.get_filename(),'w')
		    filepath = dialog.get_filename()

		    page_num = self.CodeNotebook.get_current_page()
		    buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()

		    filestream.write(buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter()))
		    filestream.close()

		    self.CodeNotebookPageVals[page_num].labelBox.get_children()[0].set_label(self.GetFileName(filepath))
		    self.CodeNotebookPageVals[page_num].filepath = filepath

		elif response == gtk.RESPONSE_CANCEL:
		    print('Closed, no files selected') #log

		dialog.destroy()
		self.loadKeywords()

	#close the app
	def QuitApp(self,widget):

		gtk.main_quit()

	#save the file if not saved already
	def SaveFileDialog(self, widget, page_num = None):
		print("savefiledialog")
		if(page_num == None):
			page_num = self.CodeNotebook.get_current_page()
		print(self.CodeNotebookPageVals[page_num])
		filepath =  self.CodeNotebookPageVals[page_num].filepath
		print("filepath :",filepath)
		if(filepath == None):
			dialog = gtk.FileChooserDialog("Save As..", None, gtk.FILE_CHOOSER_ACTION_SAVE,
											(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
			dialog.set_default_response(gtk.RESPONSE_OK)
			response = dialog.run()
			if response == gtk.RESPONSE_OK:
				filestream = open(dialog.get_filename(),'w')
				filepath = dialog.get_filename()
				self.CodeNotebookPageVals[page_num].filepath = filepath
				page_num = self.CodeNotebook.get_current_page()
				# print("\ncurrent page : "+str(page_num)+'\n')
				buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()

				filestream.write(buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter()))
				filestream.close()

				self.CodeNotebookPageVals[page_num].labelBox.get_children()[0].set_label(self.GetFileName(filepath))
				self.CodeNotebookPageVals[page_num].saveState = True

			elif response == gtk.RESPONSE_CANCEL:
				print('Closed, no files selected') #log
			dialog.destroy()
		else:
			filestream = open(filepath,'w')
			
			page_num = self.CodeNotebook.get_current_page()
			buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()
			filestream.write(buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter()))
			filestream.close()

			self.CodeNotebookPageVals[page_num].labelBox.get_children()[0].set_label(self.GetFileName(filepath))
			self.CodeNotebookPageVals[page_num].saveState = True

	# setting hotkeys
	def SetHotkeys(self):

		
		self.OpenFile.add_accelerator("activate", self.accel_group, ord('O'),gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
		self.SaveFile.add_accelerator("activate", self.accel_group, ord('S'),gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
		self.CloseFile.add_accelerator("activate", self.accel_group, ord('W'),gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
		self.Quit.add_accelerator("activate", self.accel_group, ord('Q'),gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
		self.NewEmptyFile.add_accelerator("activate", self.accel_group, ord('N'),gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
		self.Undo.add_accelerator("activate", self.accel_group, ord('Z'), gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
		self.Redo.add_accelerator("activate", self.accel_group, ord('Y'), gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
		self.Cut.add_accelerator("activate", self.accel_group, ord('X'),gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
		self.Copy.add_accelerator("activate", self.accel_group, ord('C'),gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
		self.Paste.add_accelerator("activate", self.accel_group, ord('V'),gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
		self.ReopenLastFileItem.add_accelerator("activate", self.accel_group, ord('T'), gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK, gtk.ACCEL_VISIBLE) 


	#TOOLBAR FUNCTIONS BELOW

	#creates and adds the toolbar to the window
	def CreateToolBar(self):

		#Toolbar box
		self.ToolBarBox = gtk.HBox()
		self.mainVerticalLayout.pack_start(self.ToolBarBox, fill = False, expand = False)
		#Compile and run button
		image = gtk.Image() 
		image.set_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU)
		self.CompileRunButton = gtk.Button()
		self.CompileRunButton.set_image(image)
		self.CompileRunButton.connect('clicked',self.CompileRunCode)
		self.ToolBarBox.pack_start(self.CompileRunButton, fill = False, expand = False)

		self.SearchGoogle = gtk.Button("Error Search")		
		self.SearchGoogle.connect('clicked',self.ShowGoogleResults)
		self.ToolBarBox.pack_start(self.SearchGoogle, fill = False, expand = False)		



	def GetFileExtension(self):
		page_num = self.CodeNotebook.get_current_page()
		filepath = self.CodeNotebookPageVals[page_num].filepath
		index = filepath.rfind('.')
		extension = filepath[index+1:]
		return extension

	#function called when compile&run button is click
	def CompileRunCode(self, widget):
		self.SaveFileDialog(None, None)
		extension = self.GetFileExtension()
		if(extension == 'cpp'):
			print("CPP file detected")
			self.CompileRunCodeCPP()
		elif(extension == 'R'):
			self.CompileRunCodeR()
		elif(extension == 'java'):
			print("JAVA")
		elif(extension == 'py'):
			print("Python")
			self.CompileRunCodePython()


	#compule and run R code
	def CompileRunCodeR(self):
		codefile = open('tempcode.R','w')
		page_num = self.CodeNotebook.get_current_page()
		buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()
		start_iter = buffer.get_start_iter()
		end_iter = buffer.get_end_iter()
		text = buffer.get_text(start_iter,end_iter,True)
		codefile.write(text)
		codefile.close()

		#clear console window
		buffer = self.ConsoleText.get_buffer()
		buffer.set_text('')

		#set label to compiling

		#perform compilation
		stream = subprocess.Popen(['Rscript','tempcode.R'],stdout = subprocess.PIPE,stdin = subprocess.PIPE,stderr= subprocess.PIPE)

		#get output/err
		output,err = stream.communicate()

		print("OUTPUT : \n"+output)
		print("ERROR : \n"+err)

		#if no error
		if(err == ''):
			buffer = self.ConsoleText.get_buffer()
			buffer.insert(buffer.get_end_iter(), "OUTPUT : \n"+output)
		else:
			buffer = self.ConsoleText.get_buffer()
			buffer.insert(buffer.get_end_iter(), "ERROR LOG: \n"+err)
		stream = subprocess.Popen(['rm','tempcode.R'])

	# #compule and run R code
	def CompileRunCodePython(self):
		codefile = open('tempcode.py','w')
		page_num = self.CodeNotebook.get_current_page()
		buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()
		start_iter = buffer.get_start_iter()
		end_iter = buffer.get_end_iter()
		text = buffer.get_text(start_iter,end_iter,True)
		codefile.write(text)
		codefile.close()

		#clear console window
		buffer = self.ConsoleText.get_buffer()
		buffer.set_text('')

		#set label to compiling

		#perform compilation
		stream = subprocess.Popen(['python','tempcode.py'],stdout = subprocess.PIPE,stdin = subprocess.PIPE,stderr= subprocess.PIPE)

		#get output/err
		output,err = stream.communicate()

		print("OUTPUT : \n"+output)
		print("ERROR : \n"+err)

		#if no error
		if(err == ''):
			buffer = self.ConsoleText.get_buffer()
			buffer.insert(buffer.get_end_iter(), "OUTPUT : \n"+output)
		else:
			buffer = self.ConsoleText.get_buffer()
			buffer.insert(buffer.get_end_iter(), "ERROR LOG: \n"+err)

		stream = subprocess.Popen(['rm','tempcode.py'])


	#compile and run c++ code
	def CompileRunCodeCPP(self):

		#write code to file
		codefile = open('tempcode.cpp','w')
		page_num = self.CodeNotebook.get_current_page()
		buffer = self.CodeNotebookPageVals[page_num].scrolledWindow.get_children()[0].get_buffer()
		start_iter = buffer.get_start_iter()
		end_iter = buffer.get_end_iter()
		text = buffer.get_text(start_iter,end_iter,True)
		codefile.write(text)
		codefile.close()

		#clear console window
		buffer = self.ConsoleText.get_buffer()
		buffer.set_text('')

		#set label to compiling

		#perform compilation
		stream = subprocess.Popen(['g++','tempcode.cpp'],stdout = subprocess.PIPE,stdin = subprocess.PIPE,stderr= subprocess.PIPE)

		#get output/err
		output,err = stream.communicate()

		#if no output and no error => compilation successful
		if(output == '' and err == ''):

			print("compilation successfull") #log
			buffer = self.ConsoleText.get_buffer()
			buffer.insert(buffer.get_end_iter(), "Compilation Successful\n*******\n")

			#set label to compiled
			

			#set label to running
			

			#run the code
			stream = subprocess.Popen(['./a.out'], stdout = subprocess.PIPE, stdin = subprocess.PIPE,stderr = subprocess.PIPE)
			#get output and error
			buffer = self.InputText.get_buffer()
			inputvalue = buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter())
			print(inputvalue)
			output, err = stream.communicate(inputvalue)
			# print('run output')
			# print(output)
			# print('run error')
			# print(err)

			#if no error => run successful
			if(err == ''):

				print("run successfull") #log
				buffer = self.ConsoleText.get_buffer()
				buffer.insert(buffer.get_end_iter(), "Run Successful\n*******\n")

				#store user's output and required output
				userOutput = output.rstrip()

				buffer = self.OutputText.get_buffer()
				reqOutput = (buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())).rstrip()# self.outputText.get("1.0",END).rstrip()

				print("USEROUTPUT:") #log
				print(userOutput) #log

				print("REQOUTPUT:") #log 
				print(reqOutput) #log

				#compare both outputs and set label accordingly
				if(userOutput == reqOutput):
					print("output correct") #log
					buffer = self.ConsoleText.get_buffer()
					buffer.insert(buffer.get_end_iter(), userOutput+"\n*******\noutput Correct(matches)")
				else:
					print("output incorrect") #log
					buffer = self.ConsoleText.get_buffer()
					buffer.insert(buffer.get_end_iter(), userOutput+"\n*******\noutput Incorrect (does not match)")


			else: #show runtime error
				print("runtime error")
				print(err) #log
				buffer = self.ConsoleText.get_buffer()
				buffer.insert(buffer.get_end_iter(), "RUNTIME ERROR : \n"+err)
			

			# stream = subprocess.Popen(['time','./a.out'], stdout = subprocess.PIPE, stdin = subprocess.PIPE,stderr = subprocess.PIPE)
			# output, err = stream.communicate(inputvalue)
			# print("time output")
			# print(output)
			# print("time err")
			# print(err)
			# print(err[0:err.find('elapsed')+len('elapsed')])


			#remove the temporary code file and run file
			stream = subprocess.Popen(['rm','a.out'])
			stream = subprocess.Popen(['rm','tempcode.cpp'])	



		else: #show compilation error
			print("compilation error") #log
			print(err) #log

			# buffer = gtk.TextBuffer()
			# buffer.set_text("COMPILATION ERROR : \n"+err)
			# self.ConsoleText.set_buffer(buffer)
			buffer = self.ConsoleText.get_buffer()
			buffer.insert(buffer.get_end_iter(), "COMPILATION ERROR : \n"+err)

	#google the error and create a dialog showing the results
	def ShowGoogleResults(self,widget):
		
		buffer = self.ConsoleText.get_buffer()
		err = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())
		# print(err)

		if(err == None or err == ''):
			print('nothing to search') #log
			buffer.set_text('no errors to search')
			return

		start = err.find('error:')
		#if no error found then return
		if(start == -1):
			buffer.set_text('no errors to search')
			return
		start += 6
		stop = err[start:].find('\n')
		message = err[start:][:stop]

		# Remove open and close quotes from text
		# search better way to remove this
		if(message.find('\xe2') >= 0):
			message = message[:message.find('\xe2')] + message[message.find('\xe2')+1:]
		if(message.find('\xe2') >= 0):
			message = message[:message.find('\xe2')] + message[message.find('\xe2')+1:]
		if(message.find('\x80') >= 0):
			message = message[:message.find('\x80')] + message[message.find('\x80')+1:]
		if(message.find('\x80') >= 0):
			message = message[:message.find('\x80')] + message[message.find('\x80')+1:]
		if(message.find('\x98') >= 0):
			message = message[:message.find('\x98')] + message[message.find('\x98')+1:]
		if(message.find('\x99') >= 0):
			message = message[:message.find('\x99')] + message[message.find('\x99')+1:]
		print("search query : ", message) #log
		results = pygoogle(message)

		url_list = results.get_urls()
		print(url_list) #log

		self.GoogleResultsDialog = gtk.Dialog("Google search results")
		self.GoogleResultsDialog.set_default_size(300,300)
		self.GoogleResultsDialog.set_has_separator(True)
		
		print("Total results  : ",str(len(url_list))) #log
		#Hbox to hold label and opacity entry
		for i in range(0,min(10,len(url_list))):
			vbox = gtk.VBox()
			title = gtk.Label(self.GetTitleUrl(url_list[i]))
			title.show()
			vbox.pack_start(title)
			label_text = "<span foreground = 'blue' underline = 'low'> "+url_list[i]+" </span>"
			label = gtk.Label(label_text)
			label.set_use_markup(True)
			label.set_justify(gtk.JUSTIFY_LEFT)
			label.show()
			button = gtk.Button()
			button.add(label)
			button.set_relief(gtk.RELIEF_NONE)
			button.connect("clicked",self.OpenUrl,url_list[i])
			button.show()
			vbox.pack_start(button)
			vbox.show()
			self.GoogleResultsDialog.vbox.pack_start(vbox,padding = 5)

		self.GoogleResultsDialog.run()
		self.GoogleResultsDialog.destroy()


	#returns the title of the url received from the google search for errors
	def GetTitleUrl(self,url):

		try:
			response = urllib2.urlopen(url)
			source = response.read()
			soup = bs4.BeautifulSoup(source)
			return (soup.title.string)
		except:
			print("error in getting title")#log
			return("<Page Title>")

	def OpenUrl(self,widget,url):
		webbrowser.open_new_tab(url)

	#return the filename after extracting it from the filepath
	def GetFileName(self,filepath):
		return filepath[filepath.rfind('/')+1:]

	#loads keywords (currently only cpp)
	def loadKeywords(self):

		extension = self.GetFileExtension()

		if(extension == "cpp"):
			f = open('cppkeywords.txt','r')
			self.keywords = f.readlines()
			for i in range(0,len(self.keywords)):
				self.keywords[i] = self.keywords[i].rstrip()
		elif(extension == "R"):
			f = open('rkeywords.txt','r')
			self.keywords = f.readlines()
			for i in range(0,len(self.keywords)):
				self.keywords[i] = self.keywords[i].rstrip()
		elif(extension == 'py'):
			f = open('pykeywords.txt','r')
			self.keywords = f.readlines()
			for i in range(0,len(self.keywords)):
				self.keywords[i] = self.keywords[i].rstrip()

if __name__ == "__main__":
	gtk.gdk.threads_init()
	window = MainWindow()