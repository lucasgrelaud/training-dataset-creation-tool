from PyQt5.QtCore import QDir
from PyQt5.QtCore import QTime

from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTimeEdit
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QStyle
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QInputDialog

from pyqtgraph import AxisItem
from pyqtgraph import ViewBox
from pyqtgraph import GraphicsView
from pyqtgraph import GraphicsLayout
from pyqtgraph import PlotItem
from pyqtgraph import PlotCurveItem


class DataWidget(QWidget):
    def __init__(self, parent, shared_data):
        super(DataWidget, self).__init__(parent)
        self.shared_data = shared_data
        self.shared_data.update_sync.emit()

        # Add the file selection controls
        self.dir_picker_button = QPushButton()
        self.dir_picker_button.setEnabled(True)
        self.dir_picker_button.setText("Load data")
        self.dir_picker_button.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
        self.dir_picker_button.setToolTip('Select the directory using the file explorer')
        self.dir_picker_button.clicked.connect(self.open_dir_picker)

        # Add the sync controls
        self.sync_time_label = QLabel()
        self.sync_time_label.setText('Enter the timecode (HH:mm:ss:zzz) : ')

        self.sync_time_edit = QTimeEdit()
        self.sync_time_edit.setDisplayFormat('HH:mm:ss:zzz')
        self.sync_time_edit.setEnabled(False)

        self.sync_time_button = QPushButton()
        self.sync_time_button.setText('Sync data')
        self.sync_time_button.setEnabled(False)
        self.sync_time_button.clicked.connect(self.sync_data)

        # Create the layout for the file controls
        dir_layout = QHBoxLayout()
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.addWidget(self.dir_picker_button)
        dir_layout.addStretch(1)
        dir_layout.addWidget(self.sync_time_label)
        dir_layout.addWidget(self.sync_time_edit)
        dir_layout.addWidget(self.sync_time_button)

        # Create the axis and their viewbox
        self.x_axis_item = AxisItem('left')
        self.y_axis_item = AxisItem('left')
        self.z_axis_item = AxisItem('left')

        self.x_axis_viewbox = ViewBox()
        self.y_axis_viewbox = ViewBox()
        self.z_axis_viewbox = ViewBox()

        # Create the widget which will display the data
        self.graphic_view = GraphicsView(background="#ecf0f1")
        self.graphic_layout = GraphicsLayout()
        self.graphic_view.setCentralWidget(self.graphic_layout)

        # Add the axis to the widget
        self.graphic_layout.addItem(self.x_axis_item, row=2, col=3, rowspan=1, colspan=1)
        self.graphic_layout.addItem(self.y_axis_item, row=2, col=2, rowspan=1, colspan=1)
        self.graphic_layout.addItem(self.z_axis_item, row=2, col=1, rowspan=1, colspan=1)

        self.plot_item = PlotItem()
        self.plot_item_viewbox = self.plot_item.vb
        self.graphic_layout.addItem(self.plot_item, row=2, col=4, rowspan=1, colspan=1)

        self.graphic_layout.scene().addItem(self.x_axis_viewbox)
        self.graphic_layout.scene().addItem(self.y_axis_viewbox)
        self.graphic_layout.scene().addItem(self.z_axis_viewbox)

        self.x_axis_item.linkToView(self.x_axis_viewbox)
        self.y_axis_item.linkToView(self.y_axis_viewbox)
        self.z_axis_item.linkToView(self.z_axis_viewbox)

        self.x_axis_viewbox.setXLink(self.plot_item_viewbox)
        self.y_axis_viewbox.setXLink(self.plot_item_viewbox)
        self.z_axis_viewbox.setXLink(self.plot_item_viewbox)

        self.x_axis_item.setLabel('ACC_X', color="#34495e")
        self.y_axis_item.setLabel('ACC_Y', color="#9b59b6")
        self.z_axis_item.setLabel('ACC_Z', color="#3498db")

        self.plot_item_viewbox.sigResized.connect(self.update_views)
        self.x_axis_viewbox.enableAutoRange(axis=ViewBox.XAxis, enable=True)
        self.y_axis_viewbox.enableAutoRange(axis=ViewBox.XAxis, enable=True)
        self.z_axis_viewbox.enableAutoRange(axis=ViewBox.XAxis, enable=True)

        # Create the final layout
        self.v_box = QVBoxLayout()
        self.v_box.addLayout(dir_layout)
        self.v_box.addWidget(self.graphic_view)

        self.setLayout(self.v_box)

        self.restore_state()

    def open_dir_picker(self):
        self.shared_data.data_file_path = QFileDialog.getOpenFileUrl(self, 'Open the Hexoskin data directory',
                                                                     QDir.homePath())[0]
        if self.shared_data.data_file_path is not None:
            try:
                self.load_files('ACC_X', 'ACC_Y', 'ACC_Z')
            except FileNotFoundError:
                pass
            except UnicodeDecodeError:
                pass

    def load_files(self, field1, field2, field3):
        if self.shared_data.data_file_path is not None:
            # Import the parameters from the file
            self.shared_data.import_parameter()

            # Generate the timecodes if needed
            if len(self.shared_data.parameter['TIMECODE']) == 0:
                if self.shared_data.sampling_rate is None:
                    result = False
                    while not result:
                        result = self.show_sampling_rate_picker()

                self.shared_data.add_timecode()

            # Show the 3 selected fields
            self.x_axis_viewbox.addItem(PlotCurveItem(list(map(int, self.shared_data.parameter.get(field1))),
                                                      pen='#34495e'))
            self.y_axis_viewbox.addItem(PlotCurveItem(list(map(int, self.shared_data.parameter.get(field2))),
                                                      pen='#9b59b6'))
            self.z_axis_viewbox.addItem(PlotCurveItem(list(map(int, self.shared_data.parameter.get(field3))),
                                                      pen='#3498db'))
            # Add the middle line and the bottom timecodes
            timecodes = self.shared_data.parameter['TIMECODE']
            middle = [0] * len(timecodes)
            self.plot_item_viewbox.addItem(PlotCurveItem(middle,  pen='#000000'))
            self.plot_item.getAxis('bottom').setTicks(
                self.generate_time_ticks(timecodes,self.shared_data.sampling_rate))

            # Enable the controls
            self.sync_time_edit.setEnabled(True)
            self.sync_time_button.setEnabled(True)
        self.update_views()

    def update_views(self):
        self.x_axis_viewbox.setGeometry(self.plot_item_viewbox.sceneBoundingRect())
        self.y_axis_viewbox.setGeometry(self.plot_item_viewbox.sceneBoundingRect())
        self.z_axis_viewbox.setGeometry(self.plot_item_viewbox.sceneBoundingRect())

    def generate_time_ticks(self, timecodes, rate):
        ticks = list()

        steps = [rate*30, rate*15, rate]
        for step in steps:
            temp = list()
            i = step
            while i in range(len(timecodes)):
                temp.append((i, timecodes[i].strftime('%H:%M:%S:') + str(int(timecodes[i].microsecond / 1000))))
                i += step
            ticks.append(temp)

        return ticks

    def sync_data(self):
        self.shared_data.data_sync = self.sync_time_edit.text()
        self.shared_data.update_sync.emit()

    def show_sampling_rate_picker(self) -> bool:
        self.shared_data.sampling_rate, result = QInputDialog.getInt(self, 'Set sampling rate value', 'Sampling rate')
        return result

    def restore_state(self):
        if self.shared_data.data_file_path is not None:
            self.load_files()
        if self.shared_data.data_sync is not None:
            text_time = self.shared_data.data_sync.split(':')
            time = QTime()
            time.setHMS(int(text_time[0]), int(text_time[1]), int(text_time[2]), int(text_time[3]))
            self.sync_time_edit.setTime(time)