PyCon.DE & PyData Berlin 2019 Website
================================


    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt



Edit Pages

    cd pyconde
    lektor server

Build Static Site
    
    cd pyconde
    lektor build --output-path ../www
    
The local website is run on    
[http://localhost:5000](http://localhost:5000)


Add Atom Plugin

https://github.com/ajdavis/lektor-atom

Build Talks and Tutorials (at first place the papercall submissions as
submissions.json into the root folder), then call:

    python papercall.py


