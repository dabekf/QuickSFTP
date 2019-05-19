import json
import re
from pathlib import Path, PurePosixPath

import paramiko

import sublime
import sublime_plugin

SETTINGS = "QuickSFTP.sublime-settings"
LABEL = "quick_sftp"
INIT_COMMAND = LABEL + "_init"
UPLOAD_COMMAND = LABEL + "_upload"

DEFAULTS = {
    "name": None,
    "username": None,
    "password": None,
    "knownHostsPath": None,
    "privateKeyPath": None,
    "host": None,
    "port": 22,
    "remotePath": None,
    "connectTimeout": 5,
    "directoryPermissions": "755",
    "filePermissions": "644",
    "uploadOnSave": False,
    "ignore": [],
}


def pp(text, label=None, exit_=False):
    "Simple pretty print for debugging"
    from pprint import pprint

    if label:
        print(("# DEBUG: {}".format(label)))
    pprint(text)

    if exit_:
        pass


def debug(text):
    if sublime.load_settings(SETTINGS).get("debug"):
        print("SFTP: " + text)


class SftpException(Exception):
    pass


class Connection(object):
    def __init__(self, settings):
        self.settings = settings
        self.reset()

    def reset(self):
        self.client = None
        self.connection = None
        self.pkey = None

    def upload(self, src, dst):
        if self.connection is not None:
            try:
                transport = self.client.get_transport()
                transport.send_ignore()
            except EOFError as e:
                debug("Connection reset ({})".format())
                self.reset()

        if self.connection is None:
            self.client = paramiko.SSHClient()

            if self.settings["knownHostsPath"] is not None:
                self.client.load_host_keys(self.settings["knownHostsPath"])
            else:
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.settings["privateKeyPath"] is not None:
                self.pkey = paramiko.RSAKey.from_private_key_file(self.settings["privateKeyPath"])

            self.client.connect(
                self.settings["host"],
                port=self.settings["port"],
                username=self.settings["username"],
                password=self.settings["password"],
                pkey=self.pkey,
                timeout=self.settings["connectTimeout"],
            )

            self.connection = self.client.open_sftp()
            debug("New connection open ({})".format(self.settings["name"]))
        else:
            debug("Connection reused ({})".format(self.settings["name"]))

        try:
            self.connection.put(str(src), str(dst))
        except FileNotFoundError:
            dst_path = dst.relative_to(self.settings["remotePath"])
            for parent in list(reversed(dst_path.parents))[1:]:
                p = "{}/{}".format(self.settings["remotePath"], parent)
                try:
                    self.connection.listdir(p)
                except FileNotFoundError:
                    self.connection.mkdir(p)
                    if self.settings["directoryPermissions"] is not None:
                        self.connection.chmod(p, int(self.settings["directoryPermissions"], 8))

            self.connection.put(str(src), str(dst))

        if self.settings["filePermissions"] is not None:
            self.connection.chmod(str(dst), int(self.settings["filePermissions"], 8))

        debug("{} → {}".format(src.relative_to(self.settings["projectPath"]), dst))

        return True


class Repository(object):
    connections = {}

    def __init__(self, name):
        if not name:
            raise SftpException("Field 'name' is missing in sftp.json")

        self.name = name

    def init(self, user_settings):
        settings = DEFAULTS.copy()
        settings.update(user_settings)

        for key in ["username", "host", "remotePath"]:
            if not settings[key]:
                raise SftpException("Field '{}' is required".format(key))

        self.connections[self.name] = Connection(settings)

        return settings

    def get_connection(self):
        return self.connections[self.name]

    def get_project_path(self):
        return self.connections[self.name].settings["projectPath"]

    def get_remote_path(self):
        return self.connections[self.name].settings["remotePath"]


class QuickSftpUploadCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        try:
            file_name = Path(self.view.file_name())
        except TypeError:
            self.view.erase_status(LABEL)
            return False

        try:
            name = self.view.settings().get(LABEL)["name"]
        except TypeError:
            return False

        try:
            repository = Repository(name)
            try:
                connection = repository.get_connection()
            except KeyError:
                self.view.run_command(INIT_COMMAND)
                try:
                    connection = repository.get_connection()
                except KeyError:
                    raise SftpException("Init failed")

            connection = repository.get_connection()
            project_path = connection.settings["projectPath"]
            remote_path = PurePosixPath(connection.settings["remotePath"])

            src = file_name
            relativeSrc = PurePosixPath(src.relative_to(project_path))

            for pattern in connection.settings["ignore"]:
                if re.search(pattern, str(relativeSrc)):
                    debug("Ignored file {}".format(relativeSrc))
                    return

            dst = remote_path / relativeSrc

            connection.upload(src, dst)
        except Exception as ex:
            self.view.set_status(LABEL, "SFTP: {}".format(str(ex)))
            raise
        else:
            self.view.set_status(LABEL, "done {}".format(file_name.name))
            sublime.set_timeout(lambda: self.view.set_status(LABEL, "SFTP"), 3000)


class QuickSftpInitCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        try:
            file_name = Path(self.view.file_name())
        except TypeError:
            self.view.erase_status(LABEL)
            return False

        for dir in file_name.parents:
            json_path = dir / ".sublime" / "sftp.json"
            if json_path.exists():
                debug("Found settings in {}".format(json_path))
                with json_path.open() as fp:
                    try:
                        settings = json.load(fp)
                        if "name" not in settings:
                            raise ValueError("Field 'name' is missing in sftp.json")
                    except ValueError as ex:
                        self.view.set_status(LABEL, "SFTP: {}".format(str(ex)))
                        raise

                    settings["projectPath"] = dir

                    repository = Repository(settings["name"])
                    settings = repository.init(settings)

                    self.view.settings().set(
                        LABEL, {"name": settings["name"], "uploadOnSave": settings["uploadOnSave"]}
                    )
                    self.view.set_status(LABEL, "SFTP")

                break


class QuickSftpEventListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        if not view.settings().has(LABEL):
            view.run_command(INIT_COMMAND)

    def on_pre_save_async(self, view):
        if view.settings().has(LABEL) and view.file_name() is not None:
            if view.settings().get(LABEL)["uploadOnSave"] is True:
                view.set_status(LABEL, "local → remote {}".format(Path(view.file_name()).name))

    def on_post_save_async(self, view):
        if view.settings().has(LABEL):
            if view.settings().get(LABEL)["uploadOnSave"] is True:
                view.run_command(UPLOAD_COMMAND)
