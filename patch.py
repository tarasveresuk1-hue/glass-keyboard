import re, sys
from pathlib import Path

def rd(p): return Path(p).read_text(encoding="utf-8")
def wr(p, s):
    P = Path(p); P.parent.mkdir(parents=True, exist_ok=True)
    P.write_text(s, encoding="utf-8")
def rep(p, old, new):
    t = rd(p)
    if old not in t: sys.exit(f"НЕ ЗНАЙДЕНО в {p}: {old}")
    wr(p, t.replace(old, new, 1))
def rx(p, pat, new, flags=0):
    t = rd(p)
    t2, n = re.subn(pat, lambda m: new, t, count=1, flags=flags)
    if n == 0: sys.exit(f"НЕ ЗНАЙДЕНО в {p}: {pat}")
    wr(p, t2)

wr("build.gradle", """buildscript {
    repositories { google(); mavenCentral() }
    dependencies { classpath 'com.android.tools.build:gradle:7.4.2' }
}
allprojects {
    repositories { google(); mavenCentral() }
}
""")
wr("gradle.properties", """org.gradle.jvmargs=-Xmx1536m
android.useAndroidX=true
android.nonFinalResIds=false\nandroid.suppressUnsupportedCompileSdk=34
""")
wr("app/build.gradle", """apply plugin: 'com.android.application'
android {
    namespace 'org.pocketworkstation.pckeyboard'
    compileSdk 34
    ndkVersion '26.1.10909125'
    defaultConfig {
        applicationId 'org.pocketworkstation.pckeyboard.alpha'
        minSdkVersion 21
        targetSdkVersion 34
        versionCode 1040008
        versionName "1.40.7-glass2"
        ndk { abiFilters 'armeabi-v7a', 'arm64-v8a' }
        externalNativeBuild { cmake { cppFlags "" } }
    }
    buildTypes {
        release { minifyEnabled false }
        debug { minifyEnabled false }
    }
    externalNativeBuild { cmake { path "CMakeLists.txt" } }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
    lintOptions { checkReleaseBuilds false; abortOnError false }
}
dependencies {
    implementation fileTree(include: ['*.jar'], dir: 'libs')
    implementation 'androidx.core:core:1.13.1'
}
""")

M = "app/src/main/AndroidManifest.xml"
t = rd(M)
t = re.sub(r'\s+package="[^"]*"', '', t, count=1)
if 'android:exported' not in t:
    t = t.replace('<service ', '<service android:exported="true" ')
    t = t.replace('<activity ', '<activity android:exported="true" ')
t = t.replace('<uses-permission',
    '<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>\n    <uses-permission', 1)
wr(M, t)

P = "app/src/main/java/org/pocketworkstation/pckeyboard/"
L = P + "LatinIME.java"
rep(L, "import android.support.v4.app.NotificationCompat;",
       "import androidx.core.app.NotificationCompat;\nimport androidx.core.content.ContextCompat;")
rep(L, "import android.support.v4.app.NotificationManagerCompat;",
       "import androidx.core.app.NotificationManagerCompat;")
rep(L, "registerReceiver(mNotificationReceiver, pFilter);",
       "ContextCompat.registerReceiver(this, mNotificationReceiver, pFilter, ContextCompat.RECEIVER_NOT_EXPORTED);")
t = rd(L)
t, n = re.subn(r'(PendingIntent\.getBroadcast\([^;]*?),\s*0\)',
                r'\1, PendingIntent.FLAG_IMMUTABLE)', t)
print("PendingIntent виправлено:", n)
wr(L, t)
rep(L, "super.onCreate();",
 "super.onCreate();\n        getWindow().getWindow().setBackgroundDrawable("
 "new android.graphics.drawable.ColorDrawable(android.graphics.Color.TRANSPARENT));")

NEW_INSETS = """public void onComputeInsets(InputMethodService.Insets outInsets) {
        super.onComputeInsets(outInsets);
        if (isFullscreenMode()) return;
        if (sKeyboardSettings.overlayMode) {
            android.view.View inputView = mKeyboardSwitcher.getInputView();
            android.view.View decor = getWindow().getWindow().getDecorView();
            if (inputView != null && inputView.isShown() && decor != null) {
                int[] kLoc = new int[2];
                int[] dLoc = new int[2];
                inputView.getLocationOnScreen(kLoc);
                decor.getLocationOnScreen(dLoc);
                int kbTop = kLoc[1] - dLoc[1];
                int decorH = decor.getHeight();
                outInsets.contentTopInsets = decorH;
                outInsets.visibleTopInsets = decorH;
                outInsets.touchableInsets = InputMethodService.Insets.TOUCHABLE_INSETS_REGION;
                outInsets.touchableRegion.set(0, kbTop, decor.getWidth(), decorH);
                return;
            }
        }
        outInsets.contentTopInsets = outInsets.visibleTopInsets;
    }"""
rx(L, r'public void onComputeInsets\([^)]*\)\s*\{.*?\n    \}', NEW_INSETS, re.S)

G = P + "GlobalKeyboardSettings.java"
rep(G, 'public String suggestedPunctuation = "!?,.";',
 'public String suggestedPunctuation = "!?,.";\n'
 '    public int keyboardOpacity = 100;\n    public boolean overlayMode = false;')
rep(G, "// Set initial values", """addStringPref("pref_keyboard_opacity", new StringPref() {
            public void set(String val) { keyboardOpacity = Math.round(Float.parseFloat(val)); }
            public String getDefault() { return "100"; }
            public int getFlags() { return FLAG_PREF_RECREATE_INPUT_VIEW; }
        });
        addBooleanPref("pref_overlay_mode", new BooleanPref() {
            public void set(boolean val) { overlayMode = val; }
            public boolean getDefault() { return false; }
            public int getFlags() { return FLAG_PREF_RECREATE_INPUT_VIEW; }
        });

        // Set initial values""")

S = "app/src/main/res/values/strings.xml"
rep(S, "</resources>", """    <string name="title_keyboard_opacity">Keyboard opacity</string>
    <string name="title_overlay_mode">Overlay on top of app</string>
    <string name="summary_overlay_on">App keeps its size; keyboard floats on top</string>
    <string name="summary_overlay_off">App shrinks to make room for the keyboard</string>
</resources>""")

X = "app/src/main/res/xml/prefs.xml"
t = rd(X)
i = t.find("settings_height_portrait")
if i < 0: sys.exit("НЕ ЗНАЙДЕНО в prefs.xml: settings_height_portrait")
j = t.find("/>", i) + 2
PREFS = """
    <org.pocketworkstation.pckeyboard.SeekBarPreferenceString
            android:defaultValue="100"
            hk:minValue="20" hk:maxValue="100" hk:step="5"
            hk:displayFormat="%.0f%%"
            android:key="pref_keyboard_opacity"
            android:title="@string/title_keyboard_opacity"
            android:persistent="true" />
    <CheckBoxPreference
            android:key="pref_overlay_mode"
            android:title="@string/title_overlay_mode"
            android:summaryOn="@string/summary_overlay_on"
            android:summaryOff="@string/summary_overlay_off"
            android:defaultValue="false"
            android:persistent="true" />"""
wr(X, t[:j] + PREFS + t[j:])

V = P + "LatinKeyboardBaseView.java"
rx(V, r'mPadding = new Rect\(0,\s*0,\s*0,\s*0\);',
 """int a255 = LatinIME.sKeyboardSettings.keyboardOpacity * 255 / 100;
        mKeyBackground = mKeyBackground.mutate();
        mKeyBackground.setAlpha(a255);
        if (getBackground() != null) getBackground().mutate().setAlpha(a255);
        mPadding = new Rect(0, 0, 0, 0);""")
print("OK")

import glob
for f in glob.glob("app/src/main/res/values*/strings.xml"):
    s = rd(f)
    s2 = re.sub(r'(<string name="english_ime_name"[^>]*>)[^<]*(</string>)', lambda m: m.group(1) + "Glass Keyboard" + m.group(2), s)
    if s2 != s: wr(f, s2)
wr(M, rd(M).replace("Hacker's Keyboard", "Glass Keyboard"))

# ===== GLASS v2 =====
wr("app/src/main/res/values/glass.xml", """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="glass_screen_title">Glass: look and transparency</string>
    <string name="glass_screen_summary">Opacity, button outline and fill, overlay mode</string>
    <string name="glass_cat_transparency">Transparency</string>
    <string name="glass_cat_buttons">Buttons</string>
    <string name="glass_total_opacity">Overall opacity (everything)</string>
    <string name="glass_bg_opacity">Keyboard background opacity</string>
    <string name="glass_own_style">Own button style</string>
    <string name="glass_own_style_summary">Rounded buttons with adjustable fill and outline</string>
    <string name="glass_fill_opacity">Button fill opacity</string>
    <string name="glass_fill_color">Button fill color</string>
    <string name="glass_outline_width">Outline thickness</string>
    <string name="glass_outline_opacity">Outline opacity</string>
    <string name="glass_outline_color">Outline color</string>
    <string name="glass_corner_radius">Corner radius</string>
    <string-array name="glass_fill_names">
        <item>Black</item><item>Dark gray</item><item>Dark blue</item>
        <item>Dark green</item><item>Dark red</item><item>Gray</item>
    </string-array>
    <string-array name="glass_fill_values">
        <item>#000000</item><item>#333333</item><item>#1E3A5F</item>
        <item>#1F4D2B</item><item>#5A1E1E</item><item>#666666</item>
    </string-array>
    <string-array name="glass_outline_names">
        <item>White</item><item>Green</item><item>Cyan</item>
        <item>Yellow</item><item>Orange</item><item>Red</item>
    </string-array>
    <string-array name="glass_outline_values">
        <item>#FFFFFF</item><item>#00E676</item><item>#00E5FF</item>
        <item>#FFEB3B</item><item>#FF9800</item><item>#FF5252</item>
    </string-array>
</resources>
""")

# --- prefs.xml: прибрати старі пункти, додати окремий екран
t = rd(X)
t, n = re.subn(r'\n    <org\.pocketworkstation\.pckeyboard\.SeekBarPreferenceString\s+android:defaultValue="100"\s+hk:minValue="20".*?pref_overlay_mode.*?android:persistent="true" />', '', t, count=1, flags=re.S)
if n == 0: sys.exit("НЕ ЗНАЙДЕНО в prefs.xml: старі пункти прозорості")
SCREEN = """
    <PreferenceScreen
            android:key="glass_screen"
            android:title="@string/glass_screen_title"
            android:summary="@string/glass_screen_summary">
        <PreferenceCategory android:title="@string/glass_cat_transparency">
            <org.pocketworkstation.pckeyboard.SeekBarPreferenceString
                    android:defaultValue="100" hk:minValue="5" hk:maxValue="100" hk:step="5"
                    hk:displayFormat="%.0f%%"
                    android:key="pref_keyboard_opacity"
                    android:title="@string/glass_total_opacity" android:persistent="true" />
            <org.pocketworkstation.pckeyboard.SeekBarPreferenceString
                    android:defaultValue="100" hk:minValue="0" hk:maxValue="100" hk:step="5"
                    hk:displayFormat="%.0f%%"
                    android:key="pref_bg_opacity"
                    android:title="@string/glass_bg_opacity" android:persistent="true" />
            <CheckBoxPreference
                    android:key="pref_overlay_mode"
                    android:title="@string/title_overlay_mode"
                    android:summaryOn="@string/summary_overlay_on"
                    android:summaryOff="@string/summary_overlay_off"
                    android:defaultValue="false" android:persistent="true" />
        </PreferenceCategory>
        <PreferenceCategory android:title="@string/glass_cat_buttons">
            <CheckBoxPreference
                    android:key="pref_own_style"
                    android:title="@string/glass_own_style"
                    android:summary="@string/glass_own_style_summary"
                    android:defaultValue="true" android:persistent="true" />
            <org.pocketworkstation.pckeyboard.SeekBarPreferenceString
                    android:defaultValue="100" hk:minValue="0" hk:maxValue="100" hk:step="5"
                    hk:displayFormat="%.0f%%"
                    android:key="pref_fill_opacity"
                    android:title="@string/glass_fill_opacity" android:persistent="true" />
            <ListPreference
                    android:key="pref_fill_color"
                    android:title="@string/glass_fill_color"
                    android:entries="@array/glass_fill_names"
                    android:entryValues="@array/glass_fill_values"
                    android:defaultValue="#333333" android:persistent="true" />
            <org.pocketworkstation.pckeyboard.SeekBarPreferenceString
                    android:defaultValue="2" hk:minValue="0" hk:maxValue="12" hk:step="1"
                    hk:displayFormat="%.0f"
                    android:key="pref_outline_width"
                    android:title="@string/glass_outline_width" android:persistent="true" />
            <org.pocketworkstation.pckeyboard.SeekBarPreferenceString
                    android:defaultValue="100" hk:minValue="0" hk:maxValue="100" hk:step="5"
                    hk:displayFormat="%.0f%%"
                    android:key="pref_outline_opacity"
                    android:title="@string/glass_outline_opacity" android:persistent="true" />
            <ListPreference
                    android:key="pref_outline_color"
                    android:title="@string/glass_outline_color"
                    android:entries="@array/glass_outline_names"
                    android:entryValues="@array/glass_outline_values"
                    android:defaultValue="#FFFFFF" android:persistent="true" />
            <org.pocketworkstation.pckeyboard.SeekBarPreferenceString
                    android:defaultValue="6" hk:minValue="0" hk:maxValue="20" hk:step="1"
                    hk:displayFormat="%.0f"
                    android:key="pref_corner_radius"
                    android:title="@string/glass_corner_radius" android:persistent="true" />
        </PreferenceCategory>
    </PreferenceScreen>
"""
k = t.rfind("</PreferenceScreen>")
wr(X, t[:k] + SCREEN + t[k:])

# --- GlobalKeyboardSettings: поля й реєстрація
rep(G, "public boolean overlayMode = false;", """public boolean overlayMode = false;
    public int bgOpacity = 100, fillOpacity = 100, outlineOpacity = 100;
    public int outlineWidth = 2, cornerRadius = 6;
    public boolean ownStyle = true;
    public int fillColor = 0xFF333333, outlineColor = 0xFFFFFFFF;""")

def _ip(key, field, default):
    return """addStringPref("%s", new StringPref() {
            public void set(String val) { %s = Math.round(Float.parseFloat(val)); }
            public String getDefault() { return "%s"; }
            public int getFlags() { return FLAG_PREF_RECREATE_INPUT_VIEW; }
        });
        """ % (key, field, default)

def _cp(key, field, default):
    return """addStringPref("%s", new StringPref() {
            public void set(String val) { try { %s = android.graphics.Color.parseColor(val); } catch (Exception e) { } }
            public String getDefault() { return "%s"; }
            public int getFlags() { return FLAG_PREF_RECREATE_INPUT_VIEW; }
        });
        """ % (key, field, default)

NEWP = (_ip("pref_bg_opacity", "bgOpacity", "100")
      + _ip("pref_fill_opacity", "fillOpacity", "100")
      + _ip("pref_outline_opacity", "outlineOpacity", "100")
      + _ip("pref_outline_width", "outlineWidth", "2")
      + _ip("pref_corner_radius", "cornerRadius", "6")
      + _cp("pref_fill_color", "fillColor", "#333333")
      + _cp("pref_outline_color", "outlineColor", "#FFFFFF")
      + """addBooleanPref("pref_own_style", new BooleanPref() {
            public void set(boolean val) { ownStyle = val; }
            public boolean getDefault() { return true; }
            public int getFlags() { return FLAG_PREF_RECREATE_INPUT_VIEW; }
        });

        """)
rep(G, "// Set initial values", NEWP + "// Set initial values")

# --- LatinKeyboardBaseView: метод малювання власної кнопки
GLASS_JAVA = """
    private final android.graphics.Paint mGlassFill = new android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);
    private final android.graphics.Paint mGlassStroke = new android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);

    private void drawGlassKey(android.graphics.Canvas c, int w, int h, int[] st) {
        GlobalKeyboardSettings gs = LatinIME.sKeyboardSettings;
        float dens = getResources().getDisplayMetrics().density;
        boolean hi = false;
        for (int s : st) {
            if (s == android.R.attr.state_pressed || s == android.R.attr.state_checked) hi = true;
        }
        float master = gs.keyboardOpacity / 100f;
        int base = gs.fillColor;
        int cr = android.graphics.Color.red(base);
        int cg = android.graphics.Color.green(base);
        int cb = android.graphics.Color.blue(base);
        if (hi) {
            cr += (255 - cr) * 35 / 100;
            cg += (255 - cg) * 35 / 100;
            cb += (255 - cb) * 35 / 100;
        }
        int fa = Math.round(255 * master * gs.fillOpacity / 100f);
        mGlassFill.setStyle(android.graphics.Paint.Style.FILL);
        mGlassFill.setColor(android.graphics.Color.argb(fa, cr, cg, cb));
        float sw = gs.outlineWidth * dens;
        float inset = sw / 2f + dens;
        android.graphics.RectF rect = new android.graphics.RectF(inset, inset, w - inset, h - inset);
        float rad = gs.cornerRadius * dens;
        c.drawRoundRect(rect, rad, rad, mGlassFill);
        if (sw > 0) {
            int oc = gs.outlineColor;
            int oa = Math.round(255 * master * gs.outlineOpacity / 100f);
            mGlassStroke.setStyle(android.graphics.Paint.Style.STROKE);
            mGlassStroke.setStrokeWidth(sw);
            mGlassStroke.setColor(android.graphics.Color.argb(oa,
                    android.graphics.Color.red(oc), android.graphics.Color.green(oc), android.graphics.Color.blue(oc)));
            c.drawRoundRect(rect, rad, rad, mGlassStroke);
        }
    }
"""
t = rd(V)
mm = re.search(r'public class LatinKeyboardBaseView\b[^{]*\{', t)
if not mm: sys.exit("НЕ ЗНАЙДЕНО в LatinKeyboardBaseView: оголошення класу")
wr(V, t[:mm.end()] + GLASS_JAVA + t[mm.end():])

rx(V, r'if \(mBackgroundAlpha != 255\) \{\s*keyBackground\.setAlpha\(mBackgroundAlpha\);\s*\}\s*keyBackground\.draw\(canvas\);',
 """if (LatinIME.sKeyboardSettings.ownStyle) {
                drawGlassKey(canvas, keyBackground.getBounds().right, keyBackground.getBounds().bottom, drawableState);
            } else {
                if (mBackgroundAlpha != 255) {
                    keyBackground.setAlpha(mBackgroundAlpha);
                }
                keyBackground.draw(canvas);
            }""")
rep(V, "if (getBackground() != null) getBackground().mutate().setAlpha(a255);",
       "if (getBackground() != null) getBackground().mutate().setAlpha(Math.round(a255 * LatinIME.sKeyboardSettings.bgOpacity / 100f));")
