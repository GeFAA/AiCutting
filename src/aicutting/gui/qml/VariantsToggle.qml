import QtQuick
import QtQuick.Controls.Basic
import "."

Row {
    id: root
    property bool checked: false
    property string label: "Also make teaser + short"
    property string tip: ""
    spacing: 12

    Rectangle {
        width: 46; height: 26; radius: 13
        anchors.verticalCenter: parent.verticalCenter
        color: root.checked ? Theme.accent : Theme.surface2
        border.width: 1; border.color: root.checked ? Theme.accent : Theme.hairline
        Behavior on color { ColorAnimation { duration: Theme.tMicro } }
        ToolTip.text: root.tip
        ToolTip.delay: 500
        ToolTip.visible: root.tip !== "" && ma.containsMouse
        Rectangle {
            width: 20; height: 20; radius: 10; y: 3
            x: root.checked ? 23 : 3
            color: root.checked ? Theme.canvas : Theme.textMid
            Behavior on x { NumberAnimation { duration: Theme.tMicro; easing.type: Easing.OutExpo } }
        }
        MouseArea {
            id: ma; anchors.fill: parent; hoverEnabled: true
            onClicked: root.checked = !root.checked
        }
    }
    Text {
        text: root.label
        anchors.verticalCenter: parent.verticalCenter
        font.family: Theme.fontBody; font.pixelSize: 13; color: Theme.textMid
    }
}
