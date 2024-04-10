<?php
$package = $_GET['package']; // Get the package name from the URL query string

// Paths to the XML files and screenshot directory
$infoPath = "Depictions/$package/info.xml";
$changelogPath = "Depictions/$package/changelog.xml";
$screenShotPath = "Depictions/$package/screenshots/";

// Load XML files
$info = simplexml_load_file($infoPath);
$changelog = simplexml_load_file($changelogPath);

// Start displaying HTML content
echo "<h1>" . htmlspecialchars($info->name) . "</h1>";
echo "<p>" . htmlspecialchars($info->description) . "</p>";

echo "<h2>Changelog:</h2>";
foreach ($changelog->entry as $change) {
    echo "<p><b>Version " . htmlspecialchars($change->version) . ":</b> " . htmlspecialchars($change->notes) . "</p>";
}

// Display screenshots
echo "<h2>Screenshots:</h2>";
foreach (glob($screenShotPath . "*.png") as $filename) {
    echo "<img src='$filename' style='max-width:100%; height:auto;'>";
}
?>
