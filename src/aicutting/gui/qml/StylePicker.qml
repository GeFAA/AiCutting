import QtQuick
import QtQuick.Controls.Basic
import "."

Row {
    id: root
    property string value: "cinematic"
    spacing: 6
    // [value, label, tooltip]
    readonly property var items: [
        ["cinematic", "Cinematic", "Balanced cinematic — the default look"],
        ["epic", "Epic", "Dramatic — more slow-mo and a stronger grade"],
        ["chill", "Chill", "Long, calm holds and a softer grade"],
        ["vlog", "Vlog", "Fast, punchy hard cuts — near-neutral grade"]
    ]

    Repeater {
        model: root.items
        Rectangle {
            width: 96; height: 38; radius: height / 2
            color: root.value === modelData[0] ? Qt.rgba(0.91, 0.69, 0.35, 0.14) : Theme.surface2
            border.width: 1
            border.color: root.value === modelData[0] ? Theme.accent : Theme.hairline
            Behavior on border.color { ColorAnimation { duration: Theme.tMicro } }
            Behavior on color { ColorAnimation { duration: Theme.tMicro } }
            ToolTip.text: modelData[2]
            ToolTip.delay: 500
            ToolTip.visible: ma.containsMouse
            Text {
                anchors.centerIn: parent; text: modelData[1]
                font.family: Theme.fontBody; font.pixelSize: 13
                color: root.value === modelData[0] ? Theme.textHi : Theme.textMid
            }
            MouseArea {
                id: ma; anchors.fill: parent; hoverEnabled: true
                onClicked: root.value = modelData[0]
            }
        }
    }
}
