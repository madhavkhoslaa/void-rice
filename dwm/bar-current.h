/* Fourth information field: event-driven and accurate for multi-tag views.
 * Window number is the selected client's 1-based position among visible
 * clients on THIS monitor (floating clients included); 0/0 means empty. */
static const char *
current_label(Monitor *m)
{
    static char label[96];
    size_t n = 0;
    unsigned int t, count = 0, selected = 0;
    Client *c;
    for (t = 0; t < NUMTAGS; t++)
        if (m->tagset[m->seltags] & (1U << t))
            n += snprintf(label + n, sizeof label - n, "%s%u", n ? "+" : "", t + 1);
    for (c = m->clients; c; c = c->next)
        if (ISVISIBLE(c)) {
            count++;
            if (c == m->sel)
                selected = count;
        }
    snprintf(label + n, sizeof label - n, "  \uf2d2 %u/%u", selected, count);
    return label;
}

static int
marker_width(Monitor *m)
{
    unsigned int t;
    int w = 0;
    for (t = 0; t < NUMTAGS; t++)
        w += m->tagset[m->seltags] & (1U << t) ? 30 : 14;
    return w;
}

static int
width_current(Bar *bar, BarArg *a)
{
    (void)a;
    return 50 + marker_width(bar->mon) + TEXTW(current_label(bar->mon));
}

static int
draw_current(Bar *bar, BarArg *a)
{
    unsigned int t, occupied = 0;
    int x = a->x + 50, y = a->y + a->h / 2 - 2, w;
    Client *c;
    for (c = bar->mon->clients; c; c = c->next)
        occupied |= c->tags;
    /* Void logo and a quiet divider, as in the supplied bar reference. */
    drw_setscheme(drw, scheme[SchemeTagsSel]);
    drw_text(drw, a->x, a->y, MIN(a->w, 34), a->h, 10, "\uf32e", 0, True);
    drw_setscheme(drw, scheme[SchemeHidNorm]);
    if (a->w > 40)
        drw_rect(drw, a->x + 39, a->y + 7, 1, a->h - 14, 1, 0);
    for (t = 0; t < NUMTAGS; t++) {
        int active = (bar->mon->tagset[bar->mon->seltags] & (1U << t)) != 0;
        w = active ? 22 : 4;
        if (x + w > a->x + a->w)
            break;
        drw_setscheme(drw, scheme[active ? SchemeTagsSel : (occupied & (1U << t) ? SchemeNorm : SchemeHidNorm)]);
        XSetForeground(drw->dpy, drw->gc, drw->scheme[ColFg].pixel);
        XFillArc(drw->dpy, drw->drawable, drw->gc, x, y, 4, 4, 0, 360 * 64);
        if (active) {
            drw_rect(drw, x + 2, y, 18, 4, 1, 0);
            XFillArc(drw->dpy, drw->drawable, drw->gc, x + 18, y, 4, 4, 0, 360 * 64);
        }
        x += active ? 30 : 14;
    }
    if (x >= a->x + a->w)
        return 1;
    drw_setscheme(drw, scheme[SchemeNorm]);
    return drw_text(drw, x, a->y, a->x + a->w - x, a->h, lrpad / 2,
                    current_label(bar->mon), 0, True);
}
