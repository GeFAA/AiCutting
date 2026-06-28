import QtQuick
import "."

Rectangle {
    id: root
    property string text: ""
    signal clicked
    implicitWidth: label.width + 36
    implicitHeight: 44
    radius: Theme.rMd
    color: ma.containsMouse ? Theme.surface2 : "transparent"
    border.width: 1
    border.color: ma.containsMouse ? Theme.borderFocus : Theme.hairline
    Behavior on color { ColorAnimation { duration: Theme.tMicro } }
    Behavior on border.color { ColorAnimation { duration: Theme.tMicro } }

    Text {
        id: label
        anchors.centerIn: parent; text: root.text
        font.family: Theme.fontBody; font.pixelSize: 13; color: Theme.textMid
    }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; onClicked: root.clicked() }
}
