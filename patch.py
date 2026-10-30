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
        versionCode 1040007
        versionName "v1.40.7-alpha"
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
