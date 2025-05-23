os.setenv("STARSHIP_CONFIG", "C:\\Users\\njen\\dots\\configs\\starship\\starship.toml")

os.setenv("STARSHIP_CACHE", "C:\\Users\\njen\\AppData\\Local\\Temp")

load(io.popen("starship init cmd"):read("*a"))()
