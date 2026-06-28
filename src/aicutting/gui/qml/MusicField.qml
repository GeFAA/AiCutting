import QtQuick
import "."

Rectangle {
    id: root
    property string path: ""
    signal musicDropped(string p)
    signal browseRequested
    implicitHeight: 56
    radius: Theme.rMd
    color: Theme.surface2
    border.width: 1
    border.color: da.containsDrag ? Theme.cool : Theme.hairline
    Behavior on border.color { ColorAnimation { duration: Theme.tMicro } }

    Row {
        anchors.left: parent.left; anchors.leftMargin: 18
        anchors.verticalCenter: parent.verticalCenter; spacing: 16
        Row {  // teal waveform
            spacing: 3; anchors.verticalCenter: parent.verticalCenter
            Repeater {
                model: 30
                Rectangle {
                    width: 2; radius: 1; color: Theme.cool
                    anchors.verticalCenter: parent.verticalCenter
                    height: 5 + (Math.sin(index * 0.8) * 0.5 + 0.5) * 24
                    opacity: root.path ? 0.95 : 0.32
                }
            }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.path ? root.path.split("/").pop() : "Drop a song  ·  optional"
            font.family: Theme.fontBody; font.pixelSize: 13
            color: root.path ? Theme.textHi : Theme.textLow
        }
    }
    GhostButton {
        anchors.right: parent.right; anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        text: "Choose…"; tip: "Pick a song (optional)"
        onClicked: root.browseRequested()
    }
    DropArea {
        id: da; anchors.fill: parent
        onDropped: (drop) => {
            if (drop.hasUrls && drop.urls.length > 0)
                root.musicDropped(drop.urls[0].toString().replace("file:///", ""));
        }
    }
}
