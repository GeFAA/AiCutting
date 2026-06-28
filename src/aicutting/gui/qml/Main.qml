import QtQuick
import QtQuick.Window
import QtQuick.Dialogs
import "."

Window {
    id: win
    width: 1180; height: 760
    visible: true
    title: "AiCutting Studio"
    color: Theme.canvas
    property bool advanced: false

    Rectangle {  // faint vignette
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#11151D" }
            GradientStop { position: 1.0; color: Theme.canvas }
        }
        opacity: 0.7
    }

    // ---- native pickers ----
    FolderDialog {
        id: folderDialog
        onAccepted: {
            var p = selectedFolder.toString().replace("file:///", "");
            reel.clipCount = backend.countClips(p);
            backend.setFolder(p);
        }
    }
    FileDialog {
        id: musicDialog
        nameFilters: ["Audio files (*.mp3 *.wav *.flac *.m4a *.aac *.ogg)", "All files (*)"]
        onAccepted: music.path = selectedFile.toString().replace("file:///", "")
    }
    FolderDialog {
        id: outputDialog
        onAccepted: {
            var p = selectedFolder.toString().replace("file:///", "");
            backend.setOutput(p); outputPath.text = p;
        }
    }

    Item {
        id: screens
        anchors.fill: parent
        anchors.topMargin: 30; anchors.bottomMargin: 30

        // ---- INVITE ----
        Item {
            anchors.fill: parent
            opacity: backend.status === "idle" ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Theme.tScene } }
            DropZone {
                width: 600; height: 340; anchors.centerIn: parent
                onFolderDropped: (p) => { reel.clipCount = backend.countClips(p); backend.setFolder(p); }
                onBrowseRequested: folderDialog.open()
            }
        }

        // ---- COMPOSE ----
        Item {
            anchors.fill: parent
            opacity: backend.status === "compose" ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Theme.tScene } }
            Column {
                anchors.centerIn: parent; spacing: Theme.s3; width: 600
                ReelChip { id: reel; folder: backend.chosenFolder }
                MusicField {
                    id: music; width: parent.width
                    onMusicDropped: (p) => music.path = p
                    onBrowseRequested: musicDialog.open()
                }
                Column {
                    spacing: 9
                    Text {
                        text: "STYLE"; font.family: Theme.fontDisplay; font.pixelSize: 11
                        font.letterSpacing: 2; color: Theme.textLow
                    }
                    StylePicker { id: style }
                }
                Row {
                    spacing: Theme.s4
                    Column {
                        spacing: 9
                        Text {
                            text: "ASPECT"; font.family: Theme.fontDisplay; font.pixelSize: 11
                            font.letterSpacing: 2; color: Theme.textLow
                        }
                        AspectPicker { id: aspect }
                    }
                    Column {
                        spacing: 9
                        Text {
                            text: "MASTERS"; font.family: Theme.fontDisplay; font.pixelSize: 11
                            font.letterSpacing: 2; color: Theme.textLow
                        }
                        VariantsToggle {
                            id: variants; height: 56
                            tip: "Also render a 15s teaser and a 60s short master"
                        }
                    }
                }
                GhostButton {
                    text: win.advanced ? "Advanced  ▾" : "Advanced  ▸"
                    onClicked: win.advanced = !win.advanced
                }
                Column {
                    visible: win.advanced; spacing: Theme.s2; width: parent.width
                    Row {
                        spacing: Theme.s2
                        GhostButton {
                            text: "Output folder…"; tip: "Where the cut and report are written"
                            onClicked: outputDialog.open()
                        }
                        Text {
                            id: outputPath
                            anchors.verticalCenter: parent.verticalCenter
                            text: backend.chosenFolder ? backend.defaultOutput(backend.chosenFolder) : ""
                            font.family: Theme.fontMono; font.pixelSize: 11; color: Theme.textLow
                            elide: Text.ElideMiddle; width: 420
                        }
                    }
                    VariantsToggle {
                        label: "Plan & report only — no render"
                        tip: "Create the cut plan and report without rendering the video"
                        onCheckedChanged: backend.setDryRun(checked)
                    }
                }
                Row {
                    spacing: Theme.s2
                    PrimaryButton {
                        text: "DIRECT THE CUT"
                        tip: "Analyse, edit and render the cut"
                        onClicked: backend.startCut(backend.chosenFolder, music.path,
                                                    style.value, aspect.value, variants.checked)
                    }
                    GhostButton {
                        text: "Change folder"; tip: "Pick a different footage folder"
                        onClicked: backend.reset()
                    }
                }
            }
        }

        // ---- WORKING ----
        Item {
            anchors.fill: parent
            opacity: backend.status === "working" ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Theme.tScene } }
            Column {
                anchors.centerIn: parent; spacing: Theme.s4
                StageProgress {
                    anchors.horizontalCenter: parent.horizontalCenter
                    stage: backend.stageIndex; message: backend.liveMessage
                }
                LiveStrip {
                    anchors.horizontalCenter: parent.horizontalCenter
                    hero: backend.heroImage; thumbnails: backend.liveThumbnails
                    detail: backend.liveDetail; step: backend.stepCurrent; total: backend.stepTotal
                }
                GhostButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Cancel"; tip: "Stop the current run"; onClicked: backend.cancel()
                }
            }
        }

        // ---- RESULT ----
        Item {
            anchors.fill: parent
            opacity: backend.status === "result" ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Theme.tScene } }
            Row {
                anchors.centerIn: parent; spacing: 56
                GradeDial {
                    anchors.verticalCenter: parent.verticalCenter
                    letter: backend.grade; overall: backend.gradeOverall
                    onBeat: backend.onBeat; variety: backend.variety; pacing: backend.pacing
                }
                PreviewPanel {
                    anchors.verticalCenter: parent.verticalCenter
                    source: backend.finalVideo; hasTeaser: backend.hasTeaser; hasShort: backend.hasShort
                }
            }
        }

        // ---- ERROR ----
        Item {
            anchors.fill: parent
            opacity: backend.status === "error" ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Theme.tScene } }
            Column {
                anchors.centerIn: parent; spacing: Theme.s2
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter; text: "Something went wrong"
                    font.family: Theme.fontDisplay; font.pixelSize: 22; color: Theme.danger
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter; text: backend.liveMessage
                    font.family: Theme.fontMono; font.pixelSize: 12; color: Theme.textMid
                }
                GhostButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Try again"; onClicked: backend.reset()
                }
            }
        }
    }

    // ---- letterbox frame (the signature motif) ----
    Rectangle {
        anchors.top: parent.top; width: parent.width; height: 30; color: "black"
        Rectangle {
            anchors.bottom: parent.bottom; width: parent.width; height: 1
            color: Qt.rgba(0.91, 0.69, 0.35, 0.22)
        }
        Text {
            x: 18; anchors.verticalCenter: parent.verticalCenter
            text: "AICUTTING STUDIO"; font.family: Theme.fontDisplay; font.pixelSize: 11
            font.letterSpacing: 2.4; color: Theme.textLow
        }
    }
    Rectangle {
        anchors.bottom: parent.bottom; width: parent.width; height: 30; color: "black"
        Rectangle {
            anchors.top: parent.top; width: parent.width; height: 1
            color: Qt.rgba(0.91, 0.69, 0.35, 0.22)
        }
    }
}
