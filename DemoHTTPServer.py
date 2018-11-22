#!/usr/bin/env python3


"""Simple HTTP server that handles POST, DELETE and GET requests for files.
Based on https://gist.github.com/touilleMan/eb02ea40b93e52604938 with some amount of changes
"""

__version__ = "0.1"

# place for imports
import os
import re
import html
import shutil
import hashlib
import http.server
import urllib.parse
import urllib.error
import urllib.request
from io import BytesIO

"""Demo class for HTTP server, extension of BaseHTTPRequestHandler.
Treats current working directory as a root for future mapping, creating 
new folders and searching in existing ones based on file has 
(don't forget to implement later!"""


class DemoHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    server_version = "DemoHTTPServer/" + __version__

    # define do_... functions, they will be executed after receiving corresponding HTTP request
    def do_GET(self):
        # check if we are deleting file (tunnel for html form)
        if "delete" in self.path:
            self.do_DELETE()
        else:
            # serve a GET request
            f = self.send_head()
            if f:
                self.copyfile(f, self.wfile)
                if not os.path.isdir(self.path):
                    self.path = os.path.split(self.path)[0]
                    f = self.send_head()
                f.close()

    def do_HEAD(self):
        f = self.send_head()
        if f:
            f.close()

    def do_POST(self):
        curl = True if "curl" in self.headers['User-Agent'] else False
        res, info = self.post_data()
        print((res, info, "by: ", self.client_address))
        f = BytesIO()

        if not curl:
            f.write(b'<!DOCTYPE HTML>\n')
            f.write(b'<html lang="en">\n')
            f.write(b"<title>Upload Result Page</title>\n")
            f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
            f.write(b"<hr>\n")
            if res:
                f.write(b"<strong>Success:</strong>")
            else:
                f.write(b"<strong>Failed:</strong>")
            f.write(info.encode())
            f.write(("<br><a href=\"%s\">back</a>" % self.headers['referer']).encode())
            f.write(b"</body>\n</html>\n")
        else:
            f.write(info.encode())
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def do_DELETE(self):
        res, info = self.delete_data()
        print((res, info, "by: ", self.client_address))
        f = BytesIO()
        curl = True if "curl" in self.headers['User-Agent'] else False

        # could be possibly done through decorators
        if not curl:
            f.write(b'<!DOCTYPE HTML>\n')
            f.write(b'<html lang="en">\n')
            f.write(b"<title>Delete Result Page</title>\n")
            f.write(b"<body>\n<h2>Delete Result Page</h2>\n")
            f.write(b"<hr>\n")
            if res:
                f.write(b"<strong>Success:</strong>")
            else:
                f.write(b"<strong>Failed:</strong>")
            f.write(info.encode())
            f.write(b" was successfully deleted")
            f.write(("<br><a href=\"%s\">back</a>" % self.headers['referer']).encode())
            f.write(b"</body>\n</html>\n")
        else:
            f.write(("File %s was successfully deleted" % info).encode())
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def delete_data(self):
        path, file_hash = self.translate_path(self.path)

        # check if desirable directory exists (faster than looking for a file)
        if not os.path.isdir(path):
            self.send_error(404, "File not found")
            return False, None

        full_path = path + file_hash
        try:
            os.remove(full_path)  # It is preferable to always open files in binary mode
        except OSError:
            self.send_error(404, "File not found")
            return False, None
        return True, file_hash

    def post_data(self):

        # read content-type header
        content_type = self.headers['Content-Type']

        # check if we have boundary in header
        if not content_type:
            return False, "Content-Type header does not contain boundary"
        boundary = content_type.split("=")[1].encode()

        # size of sending content
        remaining_bytes = int(self.headers['Content-Length'])

        # read line that is supposed to contain boundary
        line = self.rfile.readline()
        remaining_bytes -= len(line)
        if not boundary in line:
            return False, "Content does not begin with boundary"

        # get filenames from the next line
        line = self.rfile.readline()
        remaining_bytes -= len(line)
        fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode())
        if not fn:
            return False, "Cannot find out filename"

        # create path and filename from hashing its old name
        path = os.getcwd()
        if "\\" in path:
            path = path.split("\\")
            path = "/".join(path)
        fn_hashed = content_md5 = hashlib.md5(fn[0].encode()).hexdigest()
        folder = path + "/" + fn_hashed[:2]
        fn_hashed = folder + "/" + fn_hashed

        # read empty line
        line = self.rfile.readline()
        remaining_bytes -= len(line)

        line = self.rfile.readline()
        remaining_bytes -= len(line)

        # create folder, if it does not exist
        if not os.path.exists(folder):
            os.makedirs(folder)

        # create file with hashed name
        try:
            out = open(r'%s' % fn_hashed, 'wb')
        except IOError:
            return False, "Can't create file to write, do you have permission to write?"

        # previous line that was read
        prev_line = self.rfile.readline()
        remaining_bytes -= len(prev_line)

        # eventually send data to output file
        while remaining_bytes > 0:

            # read line after line
            line = self.rfile.readline()
            remaining_bytes -= len(line)

            # check if we reached end of file
            if boundary in line:
                prev_line = prev_line[0:-1]
                if prev_line.endswith(b'\r'):
                    prev_line = prev_line[0:-1]

                # write last line and close file
                out.write(prev_line)
                out.close()
                self.send_header("Content-MD5", content_md5)
                return True, "File '%s' was uploaded!" % fn[0]
            else:
                out.write(prev_line)
                prev_line = line
        return False, "Unexpected end of data."

    def send_head(self):
        """This is a common method used by both GET and HEAD commands.
        This sends response code and MIME headers. If the command is GET,
        then the return value is a file object (which must be closed by caller)
        or None (then callers has nothing to do)."""
        path, file_hash = self.translate_path(self.path)
        f = None
        if os.path.exists(path) and not os.path.isdir(path):
            tmp_path = path.split("/")
            file_hash = tmp_path[len(tmp_path)-1]
            path = "/".join(tmp_path[:-1]) + "/"

        if not file_hash:
            return self.list_directory(path)

        # check if desirable directory exists (faster than looking for a file)
        if not os.path.isdir(path):
            self.send_error(404, "File not found")
            return None

        full_path = path + file_hash
        try:
            f = open(full_path, 'rb')  # It is preferable to always open files in binary mode
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.send_header("Content-Disposition", "attachment; filename=\"%s\"" % file_hash)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate query in GET request to our local environment.
        If this server is running on Windows host, we'll need to change slashes in the path.
        This method returns set of items in corresponding order: current working directory plus folder,
        that is supposed to store our file (first two symbols of hash); file hash.
        """
        file_hash = re.search(r'hash=([\w]*)', path)
        if file_hash is not None:
            file_hash = file_hash.group(1)
        scipt_path = os.getcwd()
        if "\\" in scipt_path:
            scipt_path = scipt_path.split("\\")
            scipt_path = "/".join(scipt_path)

        if not os.path.isdir(scipt_path + path) and not file_hash:
            file_hash = path.split("=")[-1]
            # check if we accidentally got questionmark from url
            if "?" in file_hash:
                question = file_hash.index("?")
                file_hash = file_hash[1:] if question == 0 else file_hash[:len(file_hash) - 1]

        if not file_hash:
            scipt_path = scipt_path + urllib.parse.urlparse(path).path
            return scipt_path, None
        else:
            return scipt_path + "/" + file_hash[:2] + "/", file_hash


    def list_directory(self, path):
        """Assistant to create a directory listing (except index.html).
        Return value is either a file object, or None (indicating an
        error).
        """
        try:
            dir_list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        f = BytesIO()
        displaypath = html.escape(urllib.parse.unquote(self.path))
        curl = True if "curl" in self.headers['User-Agent'] else False
        if not curl:
            f.write(b'<!DOCTYPE HTML>\n')
            f.write(('<html lang="en">\n<title>Directory listing for %s</title>\n' % displaypath).encode())
            f.write(("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath).encode())
            f.write(b"<hr width=\"450px\" align=\"left\">\n")
            f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
            f.write(b"<input name=\"file\" type=\"file\"/>")
            f.write(b"<input type=\"submit\" value=\"upload\"/></form>\n")
            f.write(b"<hr width=\"450px\" align=\"left\">\n<ul>\n")
        else:
            f.write(("Directory listing for %s:\n" % displaypath).encode())
        if "/" in path:
            tmp_path = path.split("/")
            tmp_path = "\\".join(tmp_path)
        if not curl:
            if tmp_path != os.getcwd() + "\\":
                f.write('<li><a href="../">../</a></li>\n<hr color=\"lightgrey\" size=\"1px\"'
                        ' width=\"400px\" align=\"left\">\n'.encode())

        for name in dir_list:
            fullname = os.path.join(tmp_path, name)
            displayname = linkname = name
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if not curl:
                if not os.path.isdir(fullname):
                    f.write(('<form ENCTYPE=\"multipart/form-data\" method=\"get\" action=\"%s\">'
                             % html.escape(displayname)).encode())
                    # f.write(('<li><a href="%s">%s</a>'
                    #     % (urllib.parse.quote(linkname), html.escape(displayname))).encode())
                    f.write(('<li><input name=\"filedata\" type=\"text\" size=\"35\" '
                             'style=\"background-color:white; border: none; font-size: 14px;'
                             'font-family: Neue;\"'
                             ' disabled value=\"%s\">' % html.escape(displayname)).encode())
                    f.write(('<input type=\"submit\" value=\"Download\" formaction=\"download=%s\"/>\n'
                             % html.escape(displayname)).encode())
                    f.write(('<input type=\"submit\" value=\"Delete\" formaction=\"delete=%s\"/></form>'
                             % html.escape(displayname)).encode())
                    f.write(b"</li><hr color=\"lightgrey\" size=\"1px\" width=\"400px\" align=\"left\">\n")
                else:
                    f.write(('<li><a href="%s">%s</a></li>\n<hr color=\"lightgrey\" size=\"1px\"'
                             ' width=\"400px\" align=\"left\">\n'
                             % (urllib.parse.quote(linkname), html.escape(displayname))).encode())
            else:
                f.write(('%s\n'
                         % html.escape(displayname)).encode())
        if not curl:
            f.write(b"</ul>\n<hr width=\"450px\" align=\"left\">\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        """Copy all data between two file objects
        """
        shutil.copyfileobj(source, outputfile)


def test(HandlerClass=DemoHTTPRequestHandler,
         ServerClass=http.server.HTTPServer):
    script_path = "/".join([os.path.dirname(__file__), "storage"])
    if not os.path.exists(script_path):
        os.makedirs(script_path)
    os.chdir(script_path)
    http.server.test(HandlerClass, ServerClass)


if __name__ == '__main__':
    test()
