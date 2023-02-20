"""CompCat V0.9, developed by Mervin van Brakel. Icon art by Roos ten Hoedt."""

import nuke
from PySide2 import QtCore, QtWidgets, QtGui
import urllib
import json
import socket
import ssl

"""Finds where the CompCat plugin is stored, regardless of OS"""
for plugin_path in nuke.pluginPath():
    if "CompCat" in plugin_path:
        COMPCAT_FOLDER_PATH = plugin_path


class CompCatWindow(QtWidgets.QMainWindow):
    """Main CompCat window with multi-threading.
    Note: Qt GUI cannot be updated from within a QThread,
    which is why there are several connected functions for
    handling the UI elements seperately.
    """
    def __init__(self, parent=None):
        """Initial window setup"""
        super(CompCatWindow, self).__init__(parent)
        self.threadpool = QtCore.QThreadPool()
        self.config = load_config()

        self.loading_cat = False
        self.downloading_then_importing = False
        self.has_cat_stored = False

        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle("CompCat")

        if self.config["CompCatHTTPS"]:
            ssl._create_default_https_context = ssl.create_default_context
        else:
            ssl._create_default_https_context = ssl._create_unverified_context

        self.create_user_interface()

        self.get_new_cat_worker()

    def create_user_interface(self):
        """Creates the interface for the main CompCat window."""
        self.layout = QtWidgets.QVBoxLayout()

        if self.config["CompCatWindowOnTop"]:
            self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        self.setFixedWidth(360)
        self.setFixedHeight(480)

        """New cat button, size text & size slider."""
        self.new_cat_button = QtWidgets.QPushButton("New cat")
        self.new_cat_button.setToolTip(
            "Fetches a random new cat from the internet, yey!"
        )
        self.new_cat_button.clicked.connect(lambda: self.get_new_cat_worker())

        self.size_text = QtWidgets.QLabel("Size: ")
        self.size_text.setFont(QtGui.QFont("Arial", 8))

        self.new_cat_size_slider = QtWidgets.QSlider()
        self.new_cat_size_slider.setOrientation(QtCore.Qt.Horizontal)
        self.new_cat_size_slider.setMinimum(250)
        self.new_cat_size_slider.setMaximum(1000)
        self.new_cat_size_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.new_cat_size_slider.setTickInterval(10)
        self.new_cat_size_slider.setValue(350)
        self.new_cat_size_slider.setToolTip(
            "Increase this slider to increase the size of the cat images."
        )

        self.new_cat_layout = QtWidgets.QHBoxLayout()
        self.new_cat_layout.addWidget(self.new_cat_button, 2)
        self.new_cat_layout.addWidget(self.size_text)
        self.new_cat_layout.addWidget(self.new_cat_size_slider, 1)
        self.layout.addLayout(self.new_cat_layout)

        """QLabel where cat images and GIFs will be displayed."""
        self.cat_image_label = QtWidgets.QLabel()
        self.loading_image = QtGui.QPixmap(f"{COMPCAT_FOLDER_PATH}/Loading.png")
        self.cat_image_label.setPixmap(self.loading_image)
        self.layout.addWidget(self.cat_image_label)

        """Import & config buttons."""
        self.import_button = QtWidgets.QPushButton("Import cat")
        self.import_button.setToolTip(
            "Imports the cat image as a read node and places it in your comp."
        )
        self.import_button.clicked.connect(
            lambda: self.get_new_download_then_import_worker()
        )

        self.config_button = QtWidgets.QPushButton("Config")
        self.config_button.setToolTip(
            "Opens the CompCat config menu. Pro tip: Enable the GIFs."
        )
        self.config_button.clicked.connect(lambda: self.open_config_window())

        self.bottom_buttons_layout = QtWidgets.QHBoxLayout()
        self.bottom_buttons_layout.addWidget(self.import_button)
        self.bottom_buttons_layout.addWidget(self.config_button)
        self.layout.addLayout(self.bottom_buttons_layout)

        """Error messages & credits."""
        self.error_displayer = QtWidgets.QLabel()
        self.error_displayer.setFont(QtGui.QFont("Arial", 10))
        self.error_displayer.setWordWrap(True)

        self.credits = QtWidgets.QLabel("CompCat V0.9 | By Mervin van Brakel")

        self.layout.addWidget(self.error_displayer)
        self.layout.addWidget(self.credits)

        self.main_widget.setLayout(self.layout)

    def get_new_cat_worker(self):
        """Runs the cat get function on a seperate thread."""
        if not self.loading_cat:
            self.error_displayer.setText("")
            self.new_cat_button.setText("Loading...")
            self.worker = Worker(self.get_new_cat)
            self.worker.signals.finished.connect(self.new_cat_loaded)
            self.threadpool.start(self.worker)
            self.loading_cat = True

    def get_new_cat(self):
        """Main function that gets cat pictures using cataas.com.
        It first downloads a JSON file that represents a cat image,
        then uses that information for downloading the cat file.
        """
        try:
            self.cat_JSON = (
                urllib.request.urlopen(
                    f"https://cataas.com/cat?width={self.new_cat_size_slider.value()}&json=true"
                )
                .read()
                .decode()
            )
            self.has_succesfully_connected = True
            self.certificate_error = False
        except urllib.error.HTTPError:
            self.has_succesfully_connected = False
            self.connection_error = urllib.error.HTTPError
        except socket.gaierror:
            self.has_succesfully_connected = False
            self.connection_error = socket.gaierror
        except ssl.SSLCertVerificationError:
            self.has_succesfully_connected = False
            self.connection_error = ssl.SSLCertVerificationError
        except urllib.error.URLError as error:
            self.has_succesfully_connected = False
            self.connection_error = urllib.error.URLError
            self.error_message = error

        if self.has_succesfully_connected:
            """Keeps looking for cats that aren't GIFs, if this config option is enabled.
            It is enabled by default because downloading GIFs can be slow at times,
            and not everyone enjoys seeing moving images on their screen.
            """
            self.cat_parsed_JSON = json.loads(self.cat_JSON)

            if not self.config["CompCatGifSupport"]:
                while self.cat_parsed_JSON["mimetype"] == "image/gif":
                    self.cat_JSON = (
                        urllib.request.urlopen(
                            f"https://cataas.com/cat?width={self.new_cat_size_slider.value()}&json=true"
                        )
                        .read()
                        .decode()
                    )
                    self.cat_parsed_JSON = json.loads(self.cat_JSON)

            self.catDownload = urllib.request.urlopen(
                f"https://cataas.com{self.cat_parsed_JSON['url']}"
            )

            self.catDownloadRead = self.catDownload.read()
            self.has_cat_stored = True

    def new_cat_loaded(self):
        """This function runs when the get cat function finishes. It is only for functions that update UI elements."""
        if not self.has_succesfully_connected:
            if self.connection_error == urllib.error.HTTPError or socket.gaierror:
                self.error_displayer.setText(
                    "CompCat couldn't connect with CATAAS.com... Either there's no internet connection or the cat API is down :("
                )
            elif self.connection_error == urllib.error.URLError:
                if "CERTIFICATE_VERIFY_FAILED" in str(self.error_message):
                    self.error_displayer.setText(
                        "CompCat couldn't connect over HTTPS with CATAAS.com because your Python SSL certificates aren't properly configured. Either disable the secure HTTPS connection in the CompCat config or fix your Python SSL certificates."
                    )
                else:
                    self.error_displayer.setText(
                        "CompCat couldn't connect with CATAAS.com... Either there's no internet connection or the cat API is down :("
                    )
            else:
                self.error_displayer.setText(
                    f"Uh oh, something weird went wrong. I honestly don't know what. Sorry. Have you checked the Python console?"
                )

            self.error_image = QtGui.QPixmap(f"{COMPCAT_FOLDER_PATH}/Error.png")
            self.cat_image_label.setPixmap(self.error_image)

        else:
            if self.cat_parsed_JSON["mimetype"] == "image/gif":
                """Loads the GIF file as a QByteArray, stores it in a QBuffer and starts playing it as a QMovie."""
                self.gif_byte_array = QtCore.QByteArray(self.catDownloadRead)
                self.gif_buffer = QtCore.QBuffer(self.gif_byte_array)
                self.gif_buffer.open(QtCore.QIODevice.ReadOnly)
                self.downloaded_cat_gif = QtGui.QMovie(self.gif_buffer)
                self.downloaded_cat_gif.setCacheMode(QtGui.QMovie.CacheAll)
                self.cat_image_label.setMovie(self.downloaded_cat_gif)
                self.downloaded_cat_gif.start()

            else:
                """Loads other image files as a QPixmap."""
                self.downloaded_cat_image = QtGui.QPixmap()
                self.downloaded_cat_image.loadFromData(self.catDownloadRead)
                self.cat_image_label.setPixmap(self.downloaded_cat_image)

        self.setFixedSize(self.layout.sizeHint())
        self.new_cat_button.setText("New cat")
        self.loading_cat = False

    def get_new_download_then_import_worker(self):
        """Runs the download then import function on a seperate thread."""
        if not self.downloading_then_importing:
            self.error_displayer.setText("")
            self.worker = Worker(self.download_then_import)
            self.worker.signals.finished.connect(self.downloading_importing_done)
            self.threadpool.start(self.worker)
            self.import_button.setText("Downloading...")
            self.downloading_then_importing = True

    def download_then_import(self):
        """Function that downloads the cat file to the user-set folder."""
        self.has_succesfully_downloaded = True

        if not self.has_cat_stored:
            self.has_succesfully_downloaded = False
            self.download_error = (
                "CompCat couldn't download the cat because there is no cat."
            )

        elif self.config["CompCatFolderPath"] == "":
            self.has_succesfully_downloaded = False
            self.download_error = "CompCat couldn't import the cat because the folder where cat images are stored has not yet been set. Please do so in the CompCat config menu."

        else:
            try:
                urllib.request.urlretrieve(
                    f"https://cataas.com{self.cat_parsed_JSON['url']}",
                    f"{self.config['CompCatFolderPath']}/{self.cat_parsed_JSON['file']}",
                )

            except PermissionError:
                self.has_succesfully_downloaded = False
                self.download_error = "CompCat couldn't import the cat because it doesn't have permission to write to the selected folder. Please pick another folder or change the folder's permission settings."

            except FileNotFoundError:
                self.has_succesfully_downloaded = False
                self.download_error = "CompCat couldn't download the cat to the set file path. Are you sure the folder path is correct?"

            except Exception as error:
                self.has_succesfully_downloaded = False
                if "CERTIFICATE_VERIFY_FAILED" in str(error):
                    self.download_error = "CompCat couldn't connect over HTTPS with CATAAS.com because your Python SSL certificates aren't properly configured. Either disable the secure HTTPS connection in the CompCat config or fix your Python SSL certificates."
                else:  
                    self.download_error = f"Uh oh, something weird went wrong. Error: {error}. Please contact the dev if googling doesn't help."

    def downloading_importing_done(self):
        """This function runs when the download then import function finishes. It is only for functions that update UI elements."""
        if self.has_succesfully_downloaded:
            read_node = nuke.createNode("Read")
            read_node.knob("file").fromUserText(
                f"{self.config['CompCatFolderPath']}/{self.cat_parsed_JSON['file']}"
            )
            read_node.knob("colorspace").setValue(self.config["CompCatColorspace"])
        else:
            self.error_displayer.setText(self.download_error)

        self.import_button.setText("Import cat")
        self.setFixedSize(self.layout.sizeHint())
        self.downloading_then_importing = False

    def open_config_window(self):
        """Opens the CompCat config window and connects to it so config changes are properly synchronized."""
        self.CompCat_config_window = CompCatConfigWindow()
        self.CompCat_config_window.config_changed_signal.connect(self.config_updated)
        self.CompCat_config_window.show()

    def config_updated(self):
        """Runs when the config gets updated, so changes are synchronized."""
        self.config = load_config()

        if self.config["CompCatWindowOnTop"]:
            self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            self.show()
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
            self.show()

        if self.config["CompCatHTTPS"]:
            ssl._create_default_https_context = ssl.create_default_context
        else:
            ssl._create_default_https_context = ssl._create_unverified_context


class CompCatConfigWindow(QtWidgets.QMainWindow):
    """CompCat config window.
    It is connected to the main CompCat window, so the main window
    knows when the config is changed and can update accordingly.
    """
    config_changed_signal = QtCore.Signal()

    def __init__(self, parent=None):
        """Initial window setup"""
        super(CompCatConfigWindow, self).__init__(parent)
        self.main_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle("CompCat config")
        self.create_user_interface()

    def create_user_interface(self):
        """Creates the interface for the CompCat config window."""
        self.config = load_config()

        self.layout = QtWidgets.QVBoxLayout()
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        """Text explaining the folder textbox."""
        self.folder_path_text = QtWidgets.QLabel(
            "Folder where cat pictures will be stored:"
        )
        self.layout.addWidget(self.folder_path_text)

        """Folder path textbox with file browsing button. Initially gets set based on config."""
        self.path_to_folder_lineedit = QtWidgets.QLineEdit(
            self.config["CompCatFolderPath"]
        )
        self.path_to_folder_lineedit.setToolTip(
            "Enter the path to the folder where cat images must be saved here."
        )

        self.open_folder_browser_button = QtWidgets.QPushButton("Browse")
        self.open_folder_browser_button.clicked.connect(lambda: self.set_folder_path())
        self.open_folder_browser_button.setToolTip(
            "Click here to open a file browser menu for selecting the folder for storing cat images."
        )

        self.folder_path_layout = QtWidgets.QHBoxLayout()
        self.folder_path_layout.addWidget(self.path_to_folder_lineedit, 7)
        self.folder_path_layout.addWidget(self.open_folder_browser_button, 1)
        self.layout.addLayout(self.folder_path_layout)

        """Colorspace that is used when importing cat images. Initially gets set based on config."""
        self.colorspace_text = QtWidgets.QLabel("Import colorspace:")
        self.colorspace_lineedit = QtWidgets.QLineEdit(self.config["CompCatColorspace"])
        self.colorspace_lineedit.setToolTip("Enter the cat image colorspace here.")

        self.colorspace_layout = QtWidgets.QHBoxLayout()
        self.colorspace_layout.addWidget(self.colorspace_text, 2)
        self.colorspace_layout.addWidget(self.colorspace_lineedit, 5)
        self.layout.addLayout(self.colorspace_layout)

        """GIF checkbox. Initially gets set based on config."""
        self.gif_checkbox = QtWidgets.QCheckBox("Enable random cat GIFs")
        if self.config["CompCatGifSupport"]:
            self.gif_checkbox.setCheckState(QtCore.Qt.Checked)
        self.gif_checkbox.setToolTip(
            "Check this box to enable cat GIFs. Note: GIFs can take a lot longer to load."
        )
        self.layout.addWidget(self.gif_checkbox)

        """Window on top checkbox. Initially gets set based on config."""
        self.window_on_top_checkbox = QtWidgets.QCheckBox(
            "CompCat window is always on top"
        )
        if self.config["CompCatWindowOnTop"]:
            self.window_on_top_checkbox.setCheckState(QtCore.Qt.Checked)
        self.window_on_top_checkbox.setToolTip(
            "Check this box to always keep the CompCat window on top. Highly recommended feature."
        )
        self.layout.addWidget(self.window_on_top_checkbox)

        """HTTPS connection checkbox. Initially gets set based on config."""
        self.https_connection_checkbox = QtWidgets.QCheckBox(
            "Use secure HTTPS connection"
        )
        if self.config["CompCatHTTPS"]:
            self.https_connection_checkbox.setCheckState(QtCore.Qt.Checked)
        self.https_connection_checkbox.setToolTip(
            "Check this box to use a secure HTTPS connection. Causes some issues on certain versions of Python."
        )
        self.layout.addWidget(self.https_connection_checkbox)

        """Save button that runs the save config function."""
        self.save_button = QtWidgets.QPushButton("Save config")
        self.save_button.clicked.connect(lambda: self.save_config())
        self.save_button.setToolTip("Click here to save the config settings.")
        self.layout.addWidget(self.save_button)

        self.main_widget.setLayout(self.layout)
        self.setFixedHeight(180)

    def save_config(self):
        """Function that saves the config to the root of the current Nuke file.
        Config is stored in the Nuke file so different projects can have different cat folders.
        Also this way the plugin can be loaded from a central plugin management location so it
        can be deployed to multiple users across a network, which is obviously very necessary
        for a very important plugin like this one.
        """
        succesfully_saved_variables = 0

        """Fetching the CompCat variables by their name somehow didn't work, so instead this slightly inefficient for loop is used."""
        for index in range(nuke.Root().numKnobs()):
            if "CompCatFolderPath" in nuke.Root().knob(index).name():
                nuke.Root().knob(index).setValue(self.path_to_folder_lineedit.text())
                succesfully_saved_variables += 1
            elif "CompCatColorspace" in nuke.Root().knob(index).name():
                nuke.Root().knob(index).setValue(self.colorspace_lineedit.text())
                succesfully_saved_variables += 1
            elif "CompCatGifSupport" in nuke.Root().knob(index).name():
                nuke.Root().knob(index).setValue(self.gif_checkbox.isChecked())
                succesfully_saved_variables += 1
            elif "CompCatWindowOnTop" in nuke.Root().knob(index).name():
                nuke.Root().knob(index).setValue(
                    self.window_on_top_checkbox.isChecked()
                )
                succesfully_saved_variables += 1
            elif "CompCatHTTPS" in nuke.Root().knob(index).name():
                nuke.Root().knob(index).setValue(
                    self.https_connection_checkbox.isChecked()
                )
                succesfully_saved_variables += 1

        """Makes the variables and adds them to the Nuke file root if they don't already exist."""
        if succesfully_saved_variables != 5:
            folder_path_knob = nuke.String_Knob("CompCatFolderPath")
            nuke.Root().addKnob(folder_path_knob)
            folder_path_knob.setVisible(False)
            folder_path_knob.setValue(self.path_to_folder_lineedit.text())

            colorspace_kob = nuke.String_Knob("CompCatColorspace")
            nuke.Root().addKnob(colorspace_kob)
            colorspace_kob.setVisible(False)
            colorspace_kob.setValue(self.colorspace_lineedit.text())

            gif_support_kob = nuke.Boolean_Knob("CompCatGifSupport")
            nuke.Root().addKnob(gif_support_kob)
            gif_support_kob.setVisible(False)
            gif_support_kob.setValue(self.gif_checkbox.isChecked())

            window_top_knob = nuke.Boolean_Knob("CompCatWindowOnTop")
            nuke.Root().addKnob(window_top_knob)
            window_top_knob.setVisible(False)
            window_top_knob.setValue(self.window_on_top_checkbox.isChecked())

            https_connection_knob = nuke.Boolean_Knob("CompCatHTTPS")
            nuke.Root().addKnob(https_connection_knob)
            https_connection_knob.setVisible(False)
            https_connection_knob.setValue(self.https_connection_checkbox.isChecked())

        self.config_changed_signal.emit()
        self.close()

    def set_folder_path(self):
        """Opens up the file browser menu using a QFileDialog."""
        self.path_to_folder = str(
            QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder")
        )
        self.path_to_folder_lineedit.setText(self.path_to_folder)
        self.path_to_folder_lineedit.update()


def load_config():
    """Function that loads the config that is stored at the root of the current Nuke file.
    It uses the same slightly inefficient for loop as the save function. Oh well.
    """
    succesfully_found_variables = 0
    config_dictionary = {}
    for index in range(nuke.Root().numKnobs()):
        if "CompCatFolderPath" == nuke.Root().knob(index).name():
            config_dictionary["CompCatFolderPath"] = nuke.Root().knob(index).getValue()
            succesfully_found_variables += 1
        elif "CompCatColorspace" == nuke.Root().knob(index).name():
            config_dictionary["CompCatColorspace"] = nuke.Root().knob(index).getValue()
            succesfully_found_variables += 1
        elif "CompCatGifSupport" == nuke.Root().knob(index).name():
            config_dictionary["CompCatGifSupport"] = nuke.Root().knob(index).getValue()
            succesfully_found_variables += 1
        elif "CompCatWindowOnTop" == nuke.Root().knob(index).name():
            config_dictionary["CompCatWindowOnTop"] = nuke.Root().knob(index).getValue()
            succesfully_found_variables += 1
        elif "CompCatHTTPS" == nuke.Root().knob(index).name():
            config_dictionary["CompCatHTTPS"] = nuke.Root().knob(index).getValue()
            succesfully_found_variables += 1

    """Returns default values if no config has been set."""
    if succesfully_found_variables != 5:
        return {
            "CompCatFolderPath": "",
            "CompCatColorspace": "rec709",
            "CompCatGifSupport": False,
            "CompCatWindowOnTop": True,
            "CompCatHTTPS": False,
        }
    else:
        return config_dictionary


class Worker(QtCore.QRunnable):
    """Class for the QRunnable that runs a function on a seperate thread so Nuke doesn't freeze."""
    def __init__(self, function_to_run):
        super(Worker, self).__init__()
        self.function_to_run = function_to_run
        self.signals = WorkerSignals()

    """The run function gets executed by the QThreadPool."""
    @QtCore.Slot()
    def run(self):
        self.function_to_run()
        self.signals.finished.emit()


class WorkerSignals(QtCore.QObject):
    """Signals for the QRunnable have to be stored seperately."""
    finished = QtCore.Signal()


def open_compcat_window():
    """Opens the CompCat window. Gets executed from the menu.py file."""
    CompCat_window = CompCatWindow()
    CompCat_window.show()
