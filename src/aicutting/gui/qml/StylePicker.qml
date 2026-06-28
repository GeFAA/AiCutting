import QtQuick
import "."

Row {
    id: root
    property string value: "cinematic"
    spacing: 6
    readonly property var items: ["cinematic", "epic", "chill", "vlog"]

    Repeater {
        model: root.items
        Rectangle {
            width: 96; height: 38; radius: height / 2
            color: root.value === modelData ? Qt.rgba(0.91, 0.69, 0.35, 0.14) : Theme.surface2
            border.width: 1
            border.color: root.value === modelData ? Theme.accent : Theme.hairline
            Behavior on border.color { ColorAnimation { duration: Theme.tMicro } }
            Behavior on color { ColorAnimation { duration: Theme.tMicro } }
            Text {
                anchors.centerIn: parent
                text: modelData.charAt(0).toUpperCase() + modelData.slice(1)
                font.family: Theme.fontBody; font.pixelSize: 13
                color: root.value === modelData ? Theme.textHi : Theme.textMid
            }
            MouseArea { anchors.fill: parent; onClicked: root.value = modelData }
        }
    }
}
