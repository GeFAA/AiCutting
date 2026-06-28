import QtQuick
import QtQuick.Controls.Basic
import "."

Rectangle {
    id: root
    property string text: ""
    property string tip: ""
    signal clicked
    implicitWidth: label.width + 56
    implicitHeight: 52
    radius: Theme.rMd
    color: ma.pressed || ma.containsMouse ? Theme.accentHot : Theme.accent
    scale: ma.pressed ? 0.98 : 1.0
    Behavior on scale { NumberAnimation { duration: Theme.tMicro; easing.type: Easing.OutExpo } }
    Behavior on color { ColorAnimation { duration: Theme.tMicro } }
    ToolTip.text: root.tip
    ToolTip.delay: 500
    ToolTip.visible: root.tip !== "" && ma.containsMouse

    Rectangle {  // amber glow
        anchors.centerIn: parent
        width: parent.width + 26; height: parent.height + 26
        radius: parent.radius + 13; color: "transparent"
        border.width: 13; border.color: Qt.rgba(0.91, 0.69, 0.35, 0.16); z: -1
    }
    Text {
        id: label
        anchors.centerIn: parent; text: root.text
        font.family: Theme.fontDisplay; font.pixelSize: 16; font.letterSpacing: 1.4; font.bold: true
        color: Theme.canvas
    }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; onClicked: root.clicked() }
}
