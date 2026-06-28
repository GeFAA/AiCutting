import QtQuick
import "."

// The live "watch the AI work" panel: the frame it is looking at, the thumbnails it is rating /
// has chosen (with a scan-line sweep), a determinate done/total bar, and a one-line detail.
Column {
    id: root
    property string hero: ""
    property var thumbnails: []
    property string detail: ""
    property int step: 0
    property int total: 0
    width: 640
    spacing: Theme.s2

    Rectangle {  // hero frame (location screenshot)
        width: parent.width; height: 230; radius: Theme.rLg; color: "black"; clip: true
        visible: root.hero !== ""
        border.width: 1; border.color: Theme.hairline
        Image {
            anchors.fill: parent; fillMode: Image.PreserveAspectCrop; asynchronous: true
            source: root.hero ? "file:///" + root.hero : ""
        }
    }

    Item {  // thumbnail strip with the scan-line shimmer
        width: parent.width; height: 64; clip: true
        visible: root.thumbnails.length > 0
        Row {
            spacing: 6
            Repeater {
                model: root.thumbnails
                Rectangle {
                    width: 112; height: 63; radius: 6; color: Theme.surface2; clip: true
                    border.width: 1; border.color: Theme.hairline
                    Image {
                        anchors.fill: parent; fillMode: Image.PreserveAspectCrop; asynchronous: true
                        source: "file:///" + modelData
                    }
                }
            }
        }
        Rectangle {
            width: 2; height: parent.height; color: Theme.cool; opacity: 0.7
            SequentialAnimation on x {
                running: root.thumbnails.length > 0; loops: Animation.Infinite
                NumberAnimation { from: 0; to: root.width; duration: 1900; easing.type: Easing.InOutSine }
                NumberAnimation { from: root.width; to: 0; duration: 1900; easing.type: Easing.InOutSine }
            }
        }
    }

    Row {  // determinate sub-bar + detail
        spacing: 14; width: parent.width
        Rectangle {
            width: 320; height: 6; radius: 3; color: Theme.surface2; visible: root.total > 0
            anchors.verticalCenter: parent.verticalCenter
            Rectangle {
                height: parent.height; radius: 3; color: Theme.accent
                width: parent.width * (root.total > 0 ? root.step / root.total : 0)
                Behavior on width { NumberAnimation { duration: Theme.tControl } }
            }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.total > 0 ? (root.step + " / " + root.total) : ""
            font.family: Theme.fontMono; font.pixelSize: 12; color: Theme.textMid
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter; text: root.detail
            font.family: Theme.fontMono; font.pixelSize: 12; color: Theme.cool
        }
    }
}
