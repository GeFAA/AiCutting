import QtQuick
import "."

Row {
    id: root
    property bool checked: false
    spacing: 12

    Rectangle {
        width: 46; height: 26; radius: 13
        anchors.verticalCenter: parent.verticalCenter
        color: root.checked ? Theme.accent : Theme.surface2
        border.width: 1; border.color: root.checked ? Theme.accent : Theme.hairline
        Behavior on color { ColorAnimation { duration: Theme.tMicro } }
        Rectangle {
            width: 20; height: 20; radius: 10; y: 3
            x: root.checked ? 23 : 3
            color: root.checked ? Theme.canvas : Theme.textMid
            Behavior on x { NumberAnimation { duration: Theme.tMicro; easing.type: Easing.OutExpo } }
        }
        MouseArea { anchors.fill: parent; onClicked: root.checked = !root.checked }
    }
    Text {
        text: "Also make teaser + short"
        anchors.verticalCenter: parent.verticalCenter
        font.family: Theme.fontBody; font.pixelSize: 13; color: Theme.textMid
    }
}
