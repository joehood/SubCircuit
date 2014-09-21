del /f /s /q C:\builds\subcircuit
C:\Python27\python setup.py py2exe
xcopy /s /e /q /i subcircuit\devices C:\builds\subcircuit\devices