[app]
title = Espectrofotometro Casero
package.name = espectrofotometro
package.domain = org.aguzman
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,md
version = 0.1
requirements = python3==3.11.6,kivy==2.3.0,pillow,numpy==v1.26.4,matplotlib,plyer
# icon.filename = %(source.dir)s/icon.png
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
