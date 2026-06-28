import QtQuick
import "."

Column {
    id: root
    property string letter: ""
    property real overall: 0
    property real onBeat: 0
    property real variety: 0
    property real pacing: 0
    spacing: Theme.s3

    property real anim: 0
    onOverallChanged: { anim = 0; sweep.restart(); }
    NumberAnimation {
        id: sweep; target: root; property: "anim"
        from: 0; to: root.overall; duration: 900; easing.type: Easing.OutCubic
    }

    Item {
        width: 180; height: 180; anchors.horizontalCenter: parent.horizontalCenter
        Canvas {
            id: ring; anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d");
                ctx.reset();
                var cx = width / 2, cy = height / 2, r = 78;
                ctx.lineWidth = 10; ctx.lineCap = "round";
                ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.06);
                ctx.beginPath(); ctx.arc(cx, cy, r, 0, 2 * Math.PI); ctx.stroke();
                ctx.strokeStyle = Theme.gradeColor(root.letter);
                ctx.beginPath();
                ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * root.anim);
                ctx.stroke();
            }
            Connections { target: root; function onAnimChanged() { ring.requestPaint(); } }
        }
        Column {
            anchors.centerIn: parent; spacing: 0
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.letter || "—"; color: Theme.gradeColor(root.letter)
                font.family: Theme.fontDisplay; font.pixelSize: 66; font.bold: true
                scale: root.letter ? 1.0 : 1.3
                Behavior on scale { NumberAnimation { duration: Theme.tControl; easing.type: Easing.OutBack } }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Math.round(root.anim * 100) + "%"
                font.family: Theme.fontMono; font.pixelSize: 14; color: Theme.textMid
            }
        }
    }

    Column {
        spacing: 11; width: 248; anchors.horizontalCenter: parent.horizontalCenter
        Repeater {
            model: [["On-beat", root.onBeat], ["Variety", root.variety], ["Pacing", root.pacing]]
            Row {
                spacing: 12
                Text {
                    width: 60; text: modelData[0]
                    font.family: Theme.fontBody; font.pixelSize: 12; color: Theme.textMid
                    anchors.verticalCenter: parent.verticalCenter
                }
                Rectangle {
                    width: 150; height: 6; radius: 3; color: Theme.surface2
                    anchors.verticalCenter: parent.verticalCenter
                    Rectangle {
                        height: parent.height; radius: 3; color: Theme.cool
                        width: parent.width * Math.max(0, Math.min(1, modelData[1]))
                        Behavior on width { NumberAnimation { duration: 600; easing.type: Easing.OutCubic } }
                    }
                }
                Text {
                    text: Math.round(modelData[1] * 100) + "%"
                    font.family: Theme.fontMono; font.pixelSize: 11; color: Theme.textLow
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
