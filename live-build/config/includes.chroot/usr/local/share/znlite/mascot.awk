# User-supplied mascot shading; emit escapes only when the terminal supports them.
BEGIN {
    reset = "\033[0m"
    white = "\033[38;2;235;253;255m"
    muzzle = "\033[38;2;190;243;247m"
    highlight = "\033[38;2;135;242;242m"
    shadow = "\033[38;2;13;169;222m"
    deep = "\033[38;2;10;157;215m"
}
{
    if (mode == "plain") { print; next }
    if (mode == "ansi") { printf "\033[1;36m%s%s\n", $0, reset; next }
    row = NR
    if (row <= 18) {
        t = (row - 1) / 17
        r = int(105 - 45 * t); g = int(235 - 10 * t); b = int(232 + 3 * t)
    } else {
        t = (row - 18) / 18
        if (t > 1) t = 1
        r = int(60 - 38 * t); g = int(225 - 37 * t); b = 235
    }
    base = sprintf("\033[38;2;%d;%d;%dm", r, g, b)
    previous = ""
    for (i = 1; i <= length($0); i++) {
        c = substr($0, i, 1); color = base
        if (row == 13 && ((i >= 6 && i <= 17) || (i >= 39 && i <= 49))) color = muzzle
        if (row == 14 && ((i >= 5 && i <= 19) || (i >= 37 && i <= 51))) color = muzzle
        if (row == 15 && ((i >= 6 && i <= 21) || (i >= 35 && i <= 50))) color = muzzle
        if (row == 16 && ((i >= 11 && i <= 23) || (i >= 34 && i <= 46))) color = muzzle
        if (row == 17 && i >= 17 && i <= 40) color = muzzle
        if (row == 18 && i >= 19 && i <= 37) color = white
        if (row == 19 && i >= 21 && i <= 35) color = white
        if (color == base) {
            if (c == "X") color = highlight
            else if (c == "$") color = (row > 20 ? deep : shadow)
            else if (c == "&") color = (row >= 13 && row <= 19 ? white : highlight)
            else if (c == "." || c == ":") {
                rr = r + 13; gg = g + 10; bb = b + 7
                if (rr > 255) rr = 255
                if (gg > 255) gg = 255
                if (bb > 255) bb = 255
                color = sprintf("\033[38;2;%d;%d;%dm", rr, gg, bb)
            } else if (c == ";" || c == "+") {
                color = sprintf("\033[38;2;%d;%d;%dm", r + 5, g + 4, b + 3)
            }
        }
        if (color != previous) printf "%s", color
        printf "%s", c
        previous = color
    }
    printf "%s\n", reset
}
