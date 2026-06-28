import QtQuick
import "."

Column {
    id: root
    property string source: ""
    property bool hasTeaser: false
    property bool hasShort: false
    spacing: Theme.s2

    // Tabs (Final / Teaser / Short) shown when variant masters exist.
    Row {
        spacing: Theme.s1; visible: root.hasTeaser || root.hasShort
        Repeater {
            model: ["Final"].concat(root.hasTeaser ? ["Teaser"] : []).concat(root.hasShort ? ["Short"] : [])
            Text {
                text: modelData; font.family: Theme.fontBody; font.pixelSize: 12
                color: index === 0 ? Theme.accent : Theme.textLow
            }
        }
    }
    Rectangle {
        width: 560; height: 315; radius: Theme.rLg; color: "black"; clip: true
        border.width: 1; border.color: Theme.hairline
        Rectangle {  // play affordance
            anchors.centerIn: parent; width: 66; height: 66; radius: 33
            color: Qt.rgba(1, 1, 1, 0.08); border.width: 1; border.color: Theme.textLow
            Canvas {
                anchors.centerIn: parent; width: 22; height: 24; x: 2
                onPaint: {
                    var c = getContext("2d"); c.fillStyle = "#F2F4F7";
                    c.beginPath(); c.moveTo(3, 2); c.lineTo(21, 12); c.lineTo(3, 22); c.closePath(); c.fill();
                }
            }
        }
        Text {
            anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 12
            text: root.source ? root.source.split("/").pop() : ""
            font.family: Theme.fontMono; font.pixelSize: 11; color: Theme.textLow
        }
    }
    Row {
        spacing: Theme.s1
        PrimaryButton { text: "OPEN VIDEO"; onClicked: backend.openVideo() }
        GhostButton { text: "Report"; onClicked: backend.openReport() }
        GhostButton { text: "Folder"; onClicked: backend.openFolder() }
        GhostButton { text: "Resolve"; onClicked: backend.openInResolve() }
    }
}
