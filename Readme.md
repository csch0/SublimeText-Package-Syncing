# Package Syncing

Keep your different Sublime Test installations synchronised across different machines. This idea of the package came by reading the article on [sublime.wbond.net](https://sublime.wbond.net/docs/syncing), so you could use the manual way or simple using this package.

## Demo

An example sync between two machines; on the top Sublime Text 3 on OSX and on the bottom on Windows.

![SyncFolder](https://raw.github.com/wiki/Chris---/SublimeText-Package-Syncing/example.gif)

## Usage

Dropbox is a great choice for syncing settings but other services like Google Drive, or SkyDrive are also working fine. Just pick your personal favourite.

### First Machine

On your first machine you just have to set a proper sync folder and Package Syncing will simple save all selected files in this folder.

### Second Machine (or after a fresh installation)

On your second machine you simple have to set the sync folder and Package Syncing will automatically pull all available files from that folder. This following message dialog should appear which you just have to confirm.

![SyncFolder](https://raw.github.com/wiki/Chris---/SublimeText-Package-Syncing/sync_folder.jpg)

After a **restart** Package Control will check for missing packages and install them automatically.

### Requirements

In order to use get the benefit of automatic installation of packages across the different machines [Package Control](https://sublime.wbond.net) is required.

## Installation

### Using Package Control:

* Bring up the Command Palette (Command+Shift+P on OS X, Control+Shift+P on Linux/Windows).
* Select Package Control: Install Package.
* Select Package Syncing to install.

### Not using Package Control:

* Save files to the `Packages/Package Syncing` directory, then relaunch Sublime:
  * Linux: `~/.config/sublime-text-2|3/Packages/Package Syncing`
  * Mac: `~/Library/Application Support/Sublime Text 2|3/Packages/Package Syncing`
  * Windows: `%APPDATA%/Sublime Text 2|3/Packages/Package Syncing`

## Donating

Support this project and [others by chris][gittip] via [gittip][] or [paypal][].

[![Support via Gittip](https://rawgithub.com/chris---/Donation-Badges/master/gittip.jpeg)][gittip][![Support via PayPal](https://rawgithub.com/chris---/Donation-Badges/master/paypal.jpeg)][paypal]

[gittip]: https://www.gittip.com/Chris---
[paypal]: https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=ZWZCJPFSZNXEW

## License

All files in this package is licensed under the MIT license.

Copyright (c) 2013 Chris <chris@latexing.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.