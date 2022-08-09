# DigiScript Server

## Project Setup
```
pip install -r requirements.txt
```

## Run the server
```
python3 ./main.py
```

This requires that the client has been build first in order to server the static files

## Project Structure

### Controllers Module
The [controllers](./controllers) directory is where the classes for each controller are defined. This is further broken 
down into submodules based on function. 

### Models Module
The [models](./models) directory is where the database models are defined.

### Server Module
The [server](./server) directory is where the main application server (Tornado Web Application) is defined.

### Utils Module
The [utiles](./utils) directory is where helper functions etc are kept.