import QtQuick
import "."

Rectangle {
    id: root
    property string folder: ""
    property int clipCount: 0
    implicitWidth: row.width + 36
    implicitHeight: 56
    radius: Theme.rMd
    color: Theme.surface2
    border.width: 1; border.color: Theme.hairline

    Row {
        id: row
        anchors.left: parent.left; anchors.leftMargin: 18
        anchors.verticalCenter: parent.verticalCenter; spacing: 14
        Rectangle {
            width: 30; height: 30; radius: 7; color: Theme.accent
            anchors.verticalCenter: parent.verticalCenter
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter; spacing: 3
            Text {
                text: root.folder.split("/").pop() || "footage"
                font.family: Theme.fontBody; font.pixelSize: 14; color: Theme.textHi
            }
            Text {
                text: root.clipCount + " clips"
                font.family: Theme.fontMono; font.pixelSize: 11; color: Theme.textLow
            }
        }
    }
}
