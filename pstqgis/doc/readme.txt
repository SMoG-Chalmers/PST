
PST is a plugin application for the desktop software QGIS that combines 
space syntax with regular accessibility analysis in one tool.


Installation:

   1. Start QGIS 3.

   2. Click on "Plugins" / "Manage and Install Plugins..." to open the
      Plugin Manager dialog.

   3. Select "Install from ZIP" in the left margin.

   4. Click the "..."-button to the right of the "ZIP file"-field.

   5. Browse to and select the PST ZIP-file.

   6. Click the "Install Plugin"-button below the "ZIP file"-field (QGIS
      might show a warning here about installing plugins from untrusted
      sources).

   Alternatively, the plugin can be installed manually by unzipping the 
   PST zip file into the following folder (NOTE: If the final "plugins"
   folder doesn't exist it has to be created first).

     Windows:
       C:\Users\{USERNAME}\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins
       
       where {USERNAME} is your user name (without {}-characters).
   
     Mac:
       ~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins

   If done correctly you should end up with a folder called "pst" inside
   the "plugins" folder.


Enabling the plugin:

   1. Start QGIS 3.

   2. Click on 'Plugins' / 'Manage and Install Plugins...' to open the
      Plugin Manager dialog.

   3. Type in 'PST' in the search field. 

   4. Mark the checkbox of the PST plugin (if PST does not appear in the
      list make sure the installation above was done correctly).

   5. PST will now appear in the 'Vector' menu.

on Mac:

   6. When you run the plugin for the first time you get the warning '"libpstalgo.dylib" cannot be opened because the developer cannot be verified'.

   7. On your Mac, choose Apple menu  > System Preferences, click Security & Privacy, then click General. If the lock at the bottom left is locked, click it to unlock the preference pane.

   8. Select the sources from which you’ll allow software to be installed: App Store and identified developers.

   9. For the warning ‘“libpstalgo.dylib”’ was blocked from use because it is not from an identified developer’ click ‘Allow anyway’.

   10. Restart QGIS.