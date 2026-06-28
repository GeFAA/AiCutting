import QtQuick
import "."

Row {
    id: root
    property string value: "16:9"
    spacing: 10
    // [label, glyph width, glyph height]
    readonly property var ratios: [["16:9", 44, 25], ["9:16", 25, 44], ["1:1", 34, 34]]

    Repeater {
        model: root.ratios
        Column {
            spacing: 7
            Rectangle {
                width: 64; height: 56; radius: Theme.rMd
                color: root.value === modelData[0] ? Qt.rgba(0.91, 0.69, 0.35, 0.10) : Theme.surface2
                border.width: 1
                border.color: root.value === modelData[0] ? Theme.accent : Theme.hairline
                Behavior on border.color { ColorAnimation { duration: Theme.tMicro } }
                Rectangle {
                    anchors.centerIn: parent
                    width: modelData[1]; height: modelData[2]; radius: 3
                    color: "transparent"; border.width: 2
                    border.color: root.value === modelData[0] ? Theme.accent : Theme.textMid
                }
                MouseArea { anchors.fill: parent; onClicked: root.value = modelData[0] }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter; text: modelData[0]
                font.family: Theme.fontMono; font.pixelSize: 11
                color: root.value === modelData[0] ? Theme.textHi : Theme.textLow
            }
        }
    }
}
