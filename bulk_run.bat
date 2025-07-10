@ECHO OFF

FOR %%V IN (v0.8.53 v0.8.54 v0.8.92) DO (
  run.bat --xemu-tag %%V
)
