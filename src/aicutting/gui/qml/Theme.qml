pragma Singleton
import QtQuick

QtObject {
    // colour
    readonly property color canvas: "#0B0D10"
    readonly property color surface1: "#14171C"
    readonly property color surface2: "#1B1F26"
    readonly property color hairline: "#262B33"
    readonly property color borderFocus: "#3A424E"
    readonly property color textHi: "#F2F4F7"
    readonly property color textMid: "#9AA4B2"
    readonly property color textLow: "#5B6675"
    readonly property color accent: "#E8B15A"
    readonly property color accentHot: "#F4C06B"
    readonly property color cool: "#4FD0C0"
    readonly property color success: "#5BD6A0"
    readonly property color danger: "#E5675B"
    // spacing / radius
    readonly property int s1: 8
    readonly property int s2: 16
    readonly property int s3: 24
    readonly property int s4: 32
    readonly property int rMd: 12
    readonly property int rLg: 16
    readonly property int rXl: 20
    // type
    readonly property string fontDisplay: "Bahnschrift"
    readonly property string fontBody: "Segoe UI"
    readonly property string fontMono: "Cascadia Mono"
    // motion
    property bool reduceMotion: false
    readonly property int tMicro: reduceMotion ? 0 : 160
    readonly property int tControl: reduceMotion ? 0 : 220
    readonly property int tScene: reduceMotion ? 0 : 450

    function gradeColor(letter) {
        return letter === "A" ? success : letter === "F" ? danger : accent;
    }
}
