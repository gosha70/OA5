# Copyright (c) EGOGE - All Rights Reserved.
# This software may be used and distributed according to the terms of the Apache-2.0 license.
from typing import List

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import (QDockWidget, QFileDialog, QToolBar, QWidget, 
                             QTreeWidget, QTreeWidgetItem, QMenu, QVBoxLayout, QMessageBox)
from PySide6.QtGui import QIcon, QPixmap, QAction

from .study_stream_document_view import StudyStreamDocumentView
from study_stream_api.study_stream_subject import StudyStreamSubject
from study_stream_api.study_stream_document import StudyStreamDocument
from study_stream_api.study_stream_document_status import StudyStreamDocumentStatus
from study_stream_api.study_stream_school import StudyStreamSchool
from study_stream_api.study_stream_school_type import StudyStreamSchoolType

from embeddings.unstructured.file_type import FileType
from db.study_stream_dao import fetch_all_schools_with_related_data, create_entity


DEFAULT_CLASS_NAME = 'My Class'
DEFAULT_SCHOOL_NAME = 'My School'

class StudyStreamDirectoryPanel(QDockWidget):
    def __init__(self, 
                 parent: QObject, 
                 document_view: StudyStreamDocumentView, 
                 app_config, 
                 color_scheme, 
                 asserts_path: str, 
                 logging):
        super().__init__(parent=parent)
        self.parent = parent
        self.document_view = document_view
        self.logging = logging
        self.object_view = document_view.get_object_view()
        self.asserts_path = asserts_path
        self.color_scheme = color_scheme
        self.app_config = app_config
        self.page_index = 0  # Initialize page_index here
        self.selected_folder = None
        self.selected_file = None
        self.selected_school = None
        self.schools = []
        self.displayed_target = None 
        self.initPanel()
        self.load_study_stream_schema()

    def get_image_path(self, image_key: str)-> str:
        return self.asserts_path + self.app_config[image_key]
    
    def initPanel(self): 
        # Init icons and images
        self.class_selected_icon = QIcon(self.get_image_path("opened_class_icon")) 
        self.class_icon = QIcon(self.get_image_path("class_icon")) 
        
        self.inactive_file_icon = QIcon(self.get_image_path("inactive_file_icon"))
        self.active_file_icon = QIcon(self.get_image_path("active_file_icon"))  
        self.loading_icon = QIcon(self.get_image_path("loading_icon"))   
        self.school_selected_icon = QIcon(self.get_image_path("opened_school_icon")) 
        self.school_icon = QPixmap(self.get_image_path("school_icon")) 

        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        # Widget that holds the content of the dock
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Left Panel: Toolbar and List of PDFs
        toolbar = QToolBar("My Study")

        # Add a new school
        school_action = QAction(QIcon(self.get_image_path("new_school_icon")), 'New School', self.parent)
        school_action.triggered.connect(self.new_school)  # You need to define this method
        toolbar.addAction(school_action)

        # Add a new class
        self.new_subject_action = QAction(QIcon(self.get_image_path("new_class_icon")), 'New Class', self.parent)
        self.new_subject_action.triggered.connect(self.new_class)  # You need to define this method
        toolbar.addAction(self.new_subject_action)

        # Add a new document
        self.new_doc_action = QAction(QIcon(self.get_image_path("new_doc_icon")), 'New Document', self.parent)  # Use actual path to your icon
        self.new_doc_action.triggered.connect(self.import_document)
        toolbar.addAction(self.new_doc_action)

        # Add the refresh action
        refresh_action = QAction(QIcon(self.get_image_path("refresh_icon")), 'Refresh', self.parent)
        refresh_action.triggered.connect(self.refresh)  # Currently a no-op
        toolbar.addAction(refresh_action)
        
        toolbar.setStyleSheet(self.color_scheme["toolbar-css"])            
        # Add the toolbar to the layout
        layout.addWidget(toolbar)    

        # Tree Widget for displaying folders and files
        self.class_tree = QTreeWidget()
        self.class_tree.setHeaderHidden(True)
        self.class_tree.setStyleSheet(f"""
            QTreeWidget {{
                {self.color_scheme["main-css"]}                                 
            }}  
            QTreeWidget::item {{
                {self.color_scheme["main-css"]}    
            }}                                                  
            QTreeWidget::item:selected {{
                {self.color_scheme["selected-css"]}
            }}
            QTreeWidget::item:hover {{
                 {self.color_scheme["hover-css"]}
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: url({self.asserts_path + self.app_config['right-arrow-icon']});
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {{
                border-image: none;
                image: url({self.asserts_path + self.app_config['down-arrow-icon']});
            }}            
        """)

        self.class_tree.itemSelectionChanged.connect(self.handle_selection_changed)       
        self.class_tree.itemChanged.connect(self.on_item_changed) 
        self.class_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.class_tree.customContextMenuRequested.connect(self.on_context_menu) 
        self.class_tree.itemExpanded.connect(self.on_item_expanded)
        self.class_tree.itemCollapsed.connect(self.on_item_collapsed)
        layout.addWidget(self.class_tree)    

        # Set the main widget of the dock widget with the layout
        self.setWidget(widget)

    def refresh(self):
        reply = QMessageBox.question(self, "Refresh Directory", "Please confirm if you want to refresh the study directory !", QMessageBox.Ok | QMessageBox.Cancel)
        if reply == QMessageBox.Ok:
            """Clear all selections in the tree widget."""
            self.selected_file = None
            self.selected_folder = None    
            self.selected_school = None  
            self.class_tree.clear()
            self.class_tree.clearSelection()
            self.class_tree.setCurrentItem(None) 
            self.load_study_stream_schema() 
    
    def on_save_item(self, name: str, status: StudyStreamDocumentStatus):
        if self.selected_school:
            self.selected_school.setText(0, name)
        elif self.selected_folder:
            self.selected_folder.setText(0, name)
        elif self.selected_file:
            self.selected_file.setText(0, name)  
            if status:
                if status == StudyStreamDocumentStatus.IN_PROGRESS:
                    self.selected_file.setIcon(0, self.loading_icon)    
                elif status == StudyStreamDocumentStatus.PROCESSED:
                    self.selected_file.setIcon(0, self.active_file_icon) 
                else:   
                    self.selected_file.setIcon(0, self.inactive_file_icon)                 

    def load_study_stream_schema(self)-> List[StudyStreamSchool]:
        self.schools = fetch_all_schools_with_related_data()
        for school in self.schools:
            school_node = self.add_school(school_entity=school)
            for subject in school.subjects:
                class_node = self.add_class(subject_entity=subject, parent_node=school_node, with_select=False)
                for document in subject.documents:
                    self.add_document(document_entity=document, parent_node=class_node, with_select=False)
        
        if self.schools and len(self.schools) > 0:
            self.selected_school = self.class_tree.topLevelItem(0)
            self.class_tree.setCurrentItem(self.selected_school)
            self.class_tree.expandItem(self.selected_school)   
            self.select_school(tree_item=self.selected_school, school=self.selected_school.data(0, Qt.ItemDataRole.UserRole))
        else:            
            self.selected_school = None
            self.selected_folder = None
            self.selected_file = None    

    def on_item_expanded(self, item: QTreeWidgetItem):
        item_target = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(item_target, StudyStreamSubject):
            item.setIcon(0, self.class_selected_icon)
            if self.selected_folder is None:
                self.selected_folder = item

    def on_item_collapsed(self, item: QTreeWidgetItem):
        item_target = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(item_target, StudyStreamSubject):
            item.setIcon(0, self.class_icon)
            if item == self.selected_folder:
                self.selected_folder = None

    def on_item_changed(self, item: QTreeWidgetItem, column):
        if item.text(column).strip() == '':
            item.setText(column, DEFAULT_CLASS_NAME)  # Provide a default name if empty
            item_target = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(item_target, StudyStreamSubject):
                item_target.class_name = DEFAULT_CLASS_NAME

    def on_context_menu(self, point):
        item = self.class_tree.itemAt(point)
        if isinstance(item, QTreeWidgetItem):
            self.class_tree.setCurrentItem(item)
            menu = QMenu()
            item_target = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(item_target, StudyStreamDocument) and self.file_in_progress is None:   
                load_action = menu.addAction("Load")
            else:    
                load_action = None
            rename_action = menu.addAction("Rename")
            delete_action = menu.addAction("Delete")

            action = menu.exec_(self.class_tree.viewport().mapToGlobal(point))
            if action == rename_action:
                self.handl_edit(item)   
            elif action == delete_action:
                self.handle_delete(item)   
            elif load_action and action == load_action:     
                self.process_document(item)       

    def handle_delete(self, item: QTreeWidgetItem):
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            index = self.class_tree.indexOfTopLevelItem(item)
            self.class_tree.takeTopLevelItem(index)
    
    def handl_edit(self, item: QTreeWidgetItem):
        if item.flags() & Qt.ItemFlag.ItemIsEditable:
            new_name = item.text(0)
            item_target = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(item_target, StudyStreamDocument):
                item_target.name = new_name
            elif isinstance(item_target, StudyStreamSubject):
                item_target.class_name = new_name
                    
            self.class_tree.editItem(item, 0)  # Only edit if the item is set to be editable

    
    def new_school(self):
        school_entity = StudyStreamSchool(school_name=DEFAULT_SCHOOL_NAME, school_type=StudyStreamSchoolType.COLLEGE) 
        school_entity = create_entity(school_entity)
        self.add_school(school_entity)

    def add_school(self, school_entity: StudyStreamSchool)-> QTreeWidgetItem:        
        school_node = QTreeWidgetItem()
        school_node.setChildIndicatorPolicy
        school_node.setText(0, school_entity.name)
        school_node.setIcon(0, self.school_icon) 
        school_node.setFlags(school_node.flags() | Qt.ItemFlag.ItemIsEditable)  # Make the item editable         
        school_node.setData(0, Qt.ItemDataRole.UserRole, school_entity)
        # School is always at the top level 
        self.class_tree.addTopLevelItem(school_node)  
        self.selected_school = school_node    
        self.class_tree.editItem(school_node, 0)  # Optional

        return school_node

    def new_class(self):
        if self.selected_school is None:
            QMessageBox.warning(self, 'Blocked Creation', 'Does not support an orphan class, a school must be selected first !!!')  
            return
        subject_entity = StudyStreamSubject(class_name=DEFAULT_CLASS_NAME)
        school_entity = self.selected_school.data(0, Qt.ItemDataRole.UserRole)
        subject_entity.school_id = school_entity.id
        subject_entity = create_entity(subject_entity)

        self.add_class(subject_entity=subject_entity, parent_node=self.selected_school, with_select=True)

    def add_class(self, subject_entity: StudyStreamSubject, parent_node: QTreeWidgetItem, with_select: bool)-> QTreeWidgetItem:
        if parent_node is None:
            return  
        class_node = QTreeWidgetItem()
        class_node.setText(0, subject_entity.class_name)
        class_node.setIcon(0, self.class_icon) 
        class_node.setFlags(class_node.flags() | Qt.ItemFlag.ItemIsEditable)  # Make the item editable         
        class_node.setData(0, Qt.ItemDataRole.UserRole, subject_entity)
        parent_node.addChild(class_node)  
        if with_select:  
            self.class_tree.expandItem(parent_node) 
            self.selected_folder = class_node    
            self.class_tree.editItem(class_node, 0) 

        return class_node    
        
    def import_document(self):
        if self.selected_folder is None:
            QMessageBox.warning(self, 'Blocked Creation', 'Does not support an orphan documents, a class must be selected first !!!')    
            return
        path, _ = QFileDialog.getOpenFileName(self.parent, "Open PDF", "", "PDF files (*.pdf);;All files (*)")
        if path:
            doc_name = path.split('/')[-1]
            class_entity = self.selected_folder.data(0, Qt.ItemDataRole.UserRole)
            doc_entity = StudyStreamDocument(
                name=doc_name, 
                file_path=path, 
                file_type_enum=FileType.PDF,
                status_enum=StudyStreamDocumentStatus.NEW
            )
            doc_entity.subject_id = class_entity.id
            doc_entity = create_entity(doc_entity)
            self.add_document(document_entity=doc_entity, parent_node=self.selected_folder, with_select=True)

    def add_document(self, document_entity: StudyStreamDocument, parent_node: QTreeWidgetItem, with_select=False)-> QTreeWidgetItem: 
        if parent_node is None:      
            return   
        new_file = QTreeWidgetItem()
        new_file.setText(0, document_entity.name)
        if document_entity.status_enum == StudyStreamDocumentStatus.IN_PROGRESS:
            new_file.setIcon(0, self.loading_icon)    
        elif document_entity.status_enum == StudyStreamDocumentStatus.PROCESSED:
            new_file.setIcon(0, self.active_file_icon) 
        else:   
            new_file.setIcon(0, self.inactive_file_icon)   
        self.document_view.show_content(item=document_entity)            
        new_file.setData(0, Qt.ItemDataRole.UserRole, document_entity)
        parent_node.addChild(new_file)     
        if with_select is None:        
            self.class_tree.expandItem(parent_node)
            self.selected_file = new_file     

        return new_file   
    
    def handle_selection_changed(self):
        current_item = self.class_tree.currentItem()
        if current_item:
            item_target = current_item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(item_target, StudyStreamDocument): 
                if item_target != self.displayed_target:                    
                    self.selected_file = current_item
                    self.document_view.show_content(item=current_item)    
                    self.new_subject_action.setEnabled(False)  
                    self.new_doc_action.setEnabled(False)   
                    self.displayed_target = item_target   
                    self.document_view.show_content(item=item_target)
                    self.object_view.display_document(document=item_target, on_save_item=self.on_save_item) 
            elif isinstance(item_target, StudyStreamSubject):     
                if item_target != self.displayed_target:      
                    self.selected_folder = current_item   
                    self.selected_school = None
                    self.selected_file = None  
                    self.new_subject_action.setEnabled(False)  
                    self.new_doc_action.setEnabled(True)    
                    self.displayed_target = item_target   
                    self.object_view.display_class(subject=item_target, on_save_item=self.on_save_item)  
            elif isinstance(item_target, StudyStreamSchool):     
                if item_target != self.displayed_target:   
                    self.select_school(tree_item=current_item, school=item_target)  
    
    def select_school(self, tree_item, school: StudyStreamSchool):
        self.selected_school = tree_item
        self.selected_folder = None
        self.selected_file = None
        self.new_subject_action.setEnabled(True)
        self.new_doc_action.setEnabled(False) 
        self.displayed_target = school 
        self.object_view.display_school(school=school, on_save_item=self.on_save_item) 