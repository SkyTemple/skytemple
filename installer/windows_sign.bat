call "C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvars64.bat"
signtool sign /sha1 f60d5f48096f2af6749bf29da95b1bc07d1272ed /tr http://time.certum.pl /fd sha256 "%~1"
pause
