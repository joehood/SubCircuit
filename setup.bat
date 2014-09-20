del /f /s /q C:\builds\pyspyce
C:\Python27\python setup.py py2exe
xcopy /s /e /q /i pyspyce\devices C:\builds\pyspyce\devices