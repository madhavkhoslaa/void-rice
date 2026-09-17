/* Integrated flexipatch patches; no order-dependent pile of stock dwm diffs. */
#include "patches.def.h"
#undef VANITYGAPS_PATCH
#define VANITYGAPS_PATCH 1
#undef BAR_PADDING_PATCH
#define BAR_PADDING_PATCH 1
#undef BAR_HEIGHT_PATCH
#define BAR_HEIGHT_PATCH 1
#undef BAR_EXTRASTATUS_PATCH
#define BAR_EXTRASTATUS_PATCH 1
#undef BAR_SYSTRAY_PATCH
#define BAR_SYSTRAY_PATCH 1
#undef BAR_TAGS_PATCH
#define BAR_TAGS_PATCH 0
#undef BAR_LTSYMBOL_PATCH
#define BAR_LTSYMBOL_PATCH 0
#undef BAR_WINTITLE_PATCH
#define BAR_WINTITLE_PATCH 0
#undef NODMENU_PATCH
#define NODMENU_PATCH 1
#undef RESTARTSIG_PATCH
#define RESTARTSIG_PATCH 1
#undef SEAMLESS_RESTART_PATCH
#define SEAMLESS_RESTART_PATCH 1
#undef SAVEFLOATS_PATCH
#define SAVEFLOATS_PATCH 1
/* Native XShape rounding conflicts visually with 2px borders and double
 * clipping by picom. Leave at 0 for the toggleable picom rounding profile. */
#undef ROUNDED_CORNERS_PATCH
#define ROUNDED_CORNERS_PATCH 0
