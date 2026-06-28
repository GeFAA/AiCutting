import QtQuick
import "."

Item {
    id: root
    signal folderDropped(string path)
    property bool hover: false

    Rectangle {
        id: frame
        anchors.fill: parent
        radius: Theme.rXl
        color: Theme.surface1
        border.width: 1
        border.color: root.hover ? Theme.accent : Theme.hairline
        scale: root.hover ? 1.015 : 1.0
        Behavior on border.color { ColorAnimation { duration: Theme.tMicro } }
        Behavior on scale { NumberAnimation { duration: Theme.tMicro; easing.type: Easing.OutExpo } }

        Column {
            anchors.centerIn: parent; spacing: 12
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                font.family: Theme.fontDisplay; font.pixelSize: 24; font.letterSpacing: 2.4
                color: root.hover ? Theme.textHi : Theme.textMid
                text: "DROP YOUR DRONE FOOTAGE"
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                font.family: Theme.fontBody; font.pixelSize: 13; color: Theme.textLow
                text: "a folder of clips — the AI directs the cut"
            }
        }
        // horizontal corner ticks
        Repeater {
            model: 4
            Rectangle {
                width: 26; height: 2; color: Theme.accent; opacity: root.hover ? 1 : 0.5
                x: index % 2 === 0 ? 18 : frame.width - 44
                y: index < 2 ? 18 : frame.height - 20
                Behavior on opacity { NumberAnimation { duration: Theme.tMicro } }
            }
        }
        // vertical corner ticks
        Repeater {
            model: 4
            Rectangle {
                width: 2; height: 26; color: Theme.accent; opacity: root.hover ? 1 : 0.5
                x: index % 2 === 0 ? 18 : frame.width - 20
                y: index < 2 ? 18 : frame.height - 44
                Behavior on opacity { NumberAnimation { duration: Theme.tMicro } }
            }
        }
    }

    DropArea {
        anchors.fill: parent
        onEntered: root.hover = true
        onExited: root.hover = false
        onDropped: (drop) => {
            root.hover = false;
            if (drop.hasUrls && drop.urls.length > 0)
                root.folderDropped(drop.urls[0].toString().replace("file:///", ""));
        }
    }
}
