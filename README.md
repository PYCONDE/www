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


Build content pages (talks, tutorials, :


    python process_sessions.py
    
 Card validators
 
 Facebook  
 https://developers.facebook.com/tools/debug/sharing/
 
 LinkedIn  
 https://www.linkedin.com/post-inspector/inspect/
 
 Twitter  
 https://cards-dev.twitter.com/validator


