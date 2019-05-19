# QuickSFTP

Upload single file to remote server via sftp in Sublime Text 3.

This plugin allows you to send a file from a local project to a remote server using SFTP protocol. You can use a command from the command palette, or enable upload after save. It doesn't start external processes, instead using the Sublime Text Python interface and Python SSH library, [Paramiko](http://www.paramiko.org/). That way start times are shorter and you can reuse open connections, so subsequent uploads are even faster.

Paramiko and many of its dependencies are not packaged with Sublime Text 3. Bundled Python 3.3 is quite old now, but neccessary packages can be downloaded from [PyPI](https://pypi.org/) and extracted into user's configuration directory.

## Requirements

- Sublime Text 3 (tested with version 3.2.1 build 3207)
- pathlib dependency

## Installation

- Find your local Sublime Text 3 configuration directory
- Clone this repository in Packages/ (no Package Control yet, sorry)
- Install these packages from PyPI into Lib/python3.3/:
  - <https://pypi.org/project/asn1crypto/0.24.0/>
  - <https://pypi.org/project/bcrypt/3.1.3/>
  - <https://pypi.org/project/cffi/1.11.5/>
  - <https://pypi.org/project/cryptography/1.9/>
  - <https://pypi.org/project/enum34/1.1.6/>
  - <https://pypi.org/project/idna/2.7/>
  - <https://pypi.org/project/PyNaCl/1.1.2/>
  - <https://pypi.org/project/paramiko/2.3.3/>
  - <https://pypi.org/project/pyasn1/0.4.5/>
  - <https://pypi.org/project/six/1.12.0/>
- If you see a message about installing missing dependency (pathlib), restart Sublime Text

These versions specify compatibility with Python 3.3. I basically downloaded correct wheel (.whl) files for my system. You need files that have 'cp33' or 'none' in their name, for example *PyNaCl-1.1.2-cp33-cp33m-win_amd64.whl* or *six-1.12.0-py2.py3-none-any.whl*. Wheels are zip compressed files and can just be extracted.

## Configuration

Put sftp.json in a .sublime directory in the root directory of your project. The plugin searches upwards for every open file.
See `sftp.json.example` for possible values. Most fields should be self-explanatory, but here's some notes:

- `name` is required, it is used to cache connections and properly group files from different projects
- `filePermissions` and `directoryPermissions` are used when files and directories don't exists on remote and need to be created
- `uploadOnSave` is false by default
- `ignore` takes regular expressions relative to configuration parent directory
- Paramiko can authenticate using the `password` field or the key in `privateKeyPath`, but it can also use Pageant.

## Usage

Two commands are available:

- "QuickSFTP: Upload file" - upload file in current view (useful if `uploadOnSave` is off)
- "QuickSFTP: Reload configuration" - searches for sftp.json and reloads it (useful if changes were made)

You can bind these commands to keys using labels `quick_sftp_upload` and `quick_sftp_init` respectively.

## License

vim-sftpsync is licensed under the *MIT License*.
