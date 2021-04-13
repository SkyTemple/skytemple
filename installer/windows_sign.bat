call "C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvars64.bat"
signtool sign /sha1 86f9c61bdf6f916d2e345056146da6389a2fbcd1 /tr http://time.certum.pl /fd sha256 "%~1"
pause
