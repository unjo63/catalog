# Cosmetic Item List

### What is this application
  This application is the list of cosmetic items. You can see this list with web browser.
  This application authorize login users to edit or delete there own lists.

### How to use

1. Install Vagrant and VirtualBox
3. Launch the Vagrant VM (vagrant up)
4. Copy all files and directories under vagrant/catalog directory (which will automatically be synced to /vagrant/catalog within the VM)
5. Run application.py within the VM (python /vagrant/catalog/application.py)
6. Access and test the application by visiting http://localhost:8000 locally
7. You can see the database in JSON text form by visiting the following links
 + http://localhost:8000/users/JSON
 + http://localhost:8000/genres/JSON
 + http://localhost:8000/genre/<int:genre_id>/items/JSON

### Contents
You need to copy all the list of files and directories. Before copy those contents you should read "How to use".

* static
 - styles.css
* templates
 - deleteGenre.html
 - deleteItem.html
 - editGenre.html
 - editItem.html
 - genres.html
 - items.html
 - login.html
 - newGenre.html
 - newItem.html
 - publicgenres.html
 - publicitems.html
 - uneditable.html
+ application.py
+ client_secrets.json
+ cosmeticitems.db
+ cosmeticitems.py
+ fb_client_secrets.json
+ readme.md