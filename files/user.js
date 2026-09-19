// Load chrome/userChrome.css (Thunderbird Restyle theme)
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// Tooltips on buttons are Thunderbird's built-in default tooltip, which
// userChrome.css can't reach; these set its system colours and corner radius.
user_pref("ui.infobackground", "#3c3c41");
user_pref("ui.infotext", "#f4f4f5");
user_pref("ui.tooltipRadius", 6);

// Lets the Lucide icons in chrome/icons/lucide take on theme colours.
user_pref("svg.context-properties.content.enabled", true);

// Two-line message cards (sender + date, subject) and names without addresses.
user_pref("mail.threadpane.cardsview.rowcount", 2);
user_pref("mail.addressDisplayFormat", 2);

// Blank reading pane instead of the "Welcome to Freedom" start page.
user_pref("mailnews.start_page.enabled", false);
