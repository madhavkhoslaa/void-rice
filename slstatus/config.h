/* Native dwm bar-current.h supplies tag/window numbers with zero polling. */
const unsigned int interval = 10000;
static const char unknown_str[] = "?";
#define MAXLEN 1024
static const struct arg args[] = {
    { run_command, "%s   ", "rice-wifi-status" },
    { run_command, "\uf293 %s   ", "rice-bluetooth-status" },
    { run_command, "\uf185 %s   ", "rice-brightness-status" },
    { run_command, "\uf028 %s ", "rice-audio-status" },
    /* flexipatch splits at ';': this second status is the centered clock. */
    { datetime, ";\uf017 %s", "%H:%M  %a %d" },
};
