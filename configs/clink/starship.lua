os.setenv('STARSHIP_CONFIG', 'C:\\repos\\dots\\configs\\starship\\starship.toml')

os.setenv('STARSHIP_CACHE', 'C:\\Users\\user\\AppData\\Local\\Temp')

load(io.popen('starship init cmd'):read("*a"))()
