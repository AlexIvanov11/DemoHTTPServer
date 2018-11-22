# DemoHTTPServer

This server runs on port 8000 and creates subfolder named "storage" in its home path (if it does not exist). Then it 
changes its working directory to "<script_path>/storage".
All files from now on are stored there. The main concept is:
1) Hashing file name of uploading file
2) Get first two symbols of hash
3) Place file with new name (it is the value of hash) under the folder that is named with two first symbols of hash

Hash is being made using md5 algorithm.
Demo HTTP server provides both web and command-line interfaces.

# Web interface
Web interface is quite easy to use, folders are shown as hyperlinks, when files stored are shown as text fields
(which are disabled, so no changes could be performed). You can upload, download or delete file. To uplooad file, 
you need to choose it from your file system and press the "upload" butteon. If everything is correct, file will be 
uploaded using rules that were described before. If you decide to download file, it will be automatically downloaded
to your default downloads location. After deleting file (also, after uploading it), you'll see a web page with information 
about  performed action - whether it was successful or not. 

# Command-line interface
Command-line interface is supposed to be performed via curl. Suggested synthax of commands:
1) Perform GET request<br>
    
    To list a directory:<br> 
      curl &lt;host&gt; <br>
      curl http://localhost:8000/c1
      
    To download a file:<br>
      curl "&lt;host&gt;/?hash=&lt;file hash&gt;"<br>
      curl http://localhost:8000/?hash=635152f5c049af7bd4f87424fd59b9ab<br>
      
2) Perform POST request:<br>
    
    curl -X "POST" -F "file=@&lt;file_name&gt;" &lt;host&gt;<br>
    curl -X "POST" -F "file=@example.jpg" http://localhost:8000<br>
    
3) Perform DELETE request:<br>

    curl -X "DELETE" "&lt;host&gt;/?hash=&lt;file_hash&gt;"<br>
    curl -X "DELETE" http://localhost:8000/?hash=635152f5c049af7bd4f87424fd59b9ab<br>
    
After completing action, HTTP server will send response that will be shown in you command line.
