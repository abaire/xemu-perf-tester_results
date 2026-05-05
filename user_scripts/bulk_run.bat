@ECHO OFF

FOR %%V IN (v0.8.132 v0.8.133 v0.8.134) DO (
  run.bat --xemu-tag %%V
  run.bat --xemu-tag %%V --use-vulkan
)
