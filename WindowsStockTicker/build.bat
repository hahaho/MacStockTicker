@echo off
echo Building native Windows executable...
dotnet publish -c Release -r win-x64 --self-contained false -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o dist
echo.
echo Build completed! Check the 'dist' folder.
pause
