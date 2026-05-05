@ECHO OFF

FOR %%V IN (v0.8.132 v0.8.133 v0.8.134) DO (
  CALL "%~dp0run.bat" --xemu-tag %%V
  CALL "%~dp0run.bat" --xemu-tag %%V --use-vulkan
)
