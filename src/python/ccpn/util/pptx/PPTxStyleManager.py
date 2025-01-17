from xml.etree.ElementTree import parse, register_namespace
from zipfile import ZipFile
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR,  MSO_AUTO_SIZE, MSO_VERTICAL_ANCHOR
from pptx.dml.color import RGBColor
from xml.etree.ElementTree import parse, register_namespace

class PPTStyleManager():

    _deafultTableStyle = {
        "header_font_size"                              : 10,
        "header_font_name"                           : "Helvetica",
        "header_font_color"                            : (255, 255, 255),  # White text color for the header
        "header_bold"                                     : True,
        "header_alignment"                            : "center",
        "header_background_color"               : (106, 59, 113), # CCPNpurple
        "font_size"                                          : 10,
        "font_name"                                       : "Helvetica",
        "font_color"                                        : (0, 0, 0),  # Black text color for both rows
        "bold"                                                 : False,
        "alignment"                                        : "center",
        "border_color"                                   : (0, 0, 0),
        "border_width"                                  : 1,
        "cell_padding"                                   : 1,
        "cell_background_color"                   : (239, 235, 240),
        "cell_background_alternate_color"   : (200, 193, 201),
        }

    """Class to manage styles in PowerPoint, including placeholders and table styling."""

    def __init__(self, pptPresenation):
        """
        Initialize the style manager with a presentation instance.
        :param presentation: An instance of a PowerPoint Presentation.
        """
        self.pptPresenation = pptPresenation
        self._accentColours = self._extractThemeAccents()
        template = self.pptPresenation._presentationTemplate
        self.tableStyleOptions = template.settingsHandler.getValue('table_style', self._deafultTableStyle)

    def _extractThemeAccents(self):
        """Extracts accent colors from a PowerPoint presentation's theme.xml."""
        accentColors = {}

        # Open the PowerPoint file as a zip archive
        with ZipFile(self.pptPresenation._pptxPath, 'r') as pptxZip:
            # Locate and open theme XML file
            themeFile = [f for f in pptxZip.namelist() if 'theme/theme' in f][0]
            with pptxZip.open(themeFile) as themeXml:
                themeTree = parse(themeXml)

                # Define namespaces
                namespaces = {
                    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
                    }
                register_namespace('', namespaces['a'])

                # Extract colors from theme
                clrScheme = themeTree.find('.//a:clrScheme', namespaces)
                if clrScheme is not None:
                    for accent in range(1, 7):  # Accent1 to Accent6
                        accentElem = clrScheme.find(f".//a:accent{accent}/a:srgbClr", namespaces)
                        if accentElem is not None:
                            rgbValue = accentElem.get('val')
                            accentColors[f'accent{accent}'] = RGBColor.from_string(rgbValue)
        return accentColors

    def getTextStyle(self, layoutPlaceholder):
        """
        Parses the XML of a layout placeholder's textFrame and extracts all text style information.
        :param layoutPlaceholder: The placeholder shape from the layout slide.
        :param accentColours: A dictionary mapping schemeClr values to RGB colors.
        :return: A dictionary containing all text styles and attributes in camelCase.
        """
        fontStyles = {}

        # Access the shape XML
        shapeXml = layoutPlaceholder._element

        # Find the <p:txBody> element in the XML
        namespaces = {
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            }
        textBody = shapeXml.find('.//p:txBody', namespaces)
        if textBody is None:
            return fontStyles  # No textFrame found, return empty dict

        # Parse <a:bodyPr> for body properties
        bodyPr = textBody.find('a:bodyPr', namespaces)
        if bodyPr is not None:
            fontStyles['anchor'] = bodyPr.get('anchor', None)
            fontStyles['autofit'] = bodyPr.find('a:normAutofit', namespaces) is not None
            fontStyles['wrap'] = bodyPr.get('wrap', None)

        # Parse <a:lstStyle> for list style properties
        lstStyle = textBody.find('a:lstStyle', namespaces)
        if lstStyle is not None:
            for level in range(1, 10):  # Check levels 1 to 9
                lvlTag = f'a:lvl{level}pPr'
                lvlPPr = lstStyle.find(lvlTag, namespaces)
                if lvlPPr is not None:
                    levelKey = f'level{level}'
                    fontStyles[levelKey] = {}
                    fontStyles[levelKey]['marginLeft'] = lvlPPr.get('marL', None)
                    fontStyles[levelKey]['indent'] = lvlPPr.get('indent', None)
                    fontStyles[levelKey]['alignment'] = lvlPPr.get('algn', None)
                    fontStyles[levelKey]['bulletType'] = 'none' if lvlPPr.find('a:buNone', namespaces) is not None else 'default'

                    # Default run properties
                    defRPr = lvlPPr.find('a:defRPr', namespaces)
                    if defRPr is not None:
                        fontSize = defRPr.get('sz')
                        if fontSize:
                            fontStyles[levelKey]['fontSize'] = int(fontSize) / 100  # Convert from centipoints to points
                        else:
                            fontStyles[levelKey]['fontSize'] = 10  # default

                        fontStyles[levelKey]['bold'] = defRPr.get('b', None)

                        # Extract font typeface
                        latin = defRPr.find('a:latin', namespaces)
                        if latin is not None:
                            fontStyles[levelKey]['fontTypeface'] = latin.get('typeface', None)

                        # Extract font color
                        solidFill = defRPr.find('a:solidFill', namespaces)
                        if solidFill is not None:
                            # Check for schemeClr
                            schemeClr = solidFill.find('a:schemeClr', namespaces)
                            if schemeClr is not None:
                                schemeColorName = schemeClr.get('val')
                                if schemeColorName in self._accentColours:
                                    fontStyles[levelKey]['fontColor'] = self._accentColours[schemeColorName]
                                else:
                                    fontStyles[levelKey]['fontColor'] = "RGB(0,0,0)"  # Default if schemeClr isn't mapped
                            else:
                                # Check for solid RGB color
                                srgbClr = solidFill.find('a:srgbClr', namespaces)
                                if srgbClr is not None:
                                    fontStyles[levelKey]['fontColor'] = f"#{srgbClr.get('val')}"

        # Parse text paragraphs and runs
        fontStyles['paragraphs'] = []
        for paragraph in textBody.findall('a:p', namespaces):
            paraDict = {}

            # Paragraph properties
            pPr = paragraph.find('a:pPr', namespaces)
            if pPr is not None:
                paraDict['level'] = pPr.get('lvl', None)
                defRPr = pPr.find('a:defRPr', namespaces)
                if defRPr is not None:
                    paraDict['defaultFontSize'] = defRPr.get('sz', 10)

            # Extract text runs
            paraDict['runs'] = []
            for run in paragraph.findall('a:r', namespaces):
                runDict = {}
                rPr = run.find('a:rPr', namespaces)
                if rPr is not None:
                    runDict['language'] = rPr.get('lang', None)
                    runDict['dirty'] = rPr.get('dirty', None)
                text = run.find('a:t', namespaces)
                if text is not None:
                    runDict['text'] = text.text
                paraDict['runs'].append(runDict)

            # Add paragraph to the paragraphs list
            fontStyles['paragraphs'].append(paraDict)

        return fontStyles

    def _insertTextAndApplyStyle(self, text, textBox, layoutPlaceholder, fontSizePt=None):
        """Insert the given text to the textBox and apply the layoutPlaceholder style.
        Adjust font size to fit the box if necessary, without resetting the size after.
        """
        textStyle = self.getTextStyle(layoutPlaceholder)
        # Get the text frame from the placeholder
        textFrame = textBox.text_frame

        # Apply body properties (don't reset font size here, leave it for later)
        if 'anchor' in textStyle:
            # Map anchor strings to MSO_VERTICAL_ANCHOR enum values
            anchor_map = {
                'top'   : MSO_VERTICAL_ANCHOR.TOP,
                'middle': MSO_VERTICAL_ANCHOR.MIDDLE,
                'bottom': MSO_VERTICAL_ANCHOR.BOTTOM
                }
            # Default to TOP if the anchor is not valid
            textFrame.vertical_anchor = anchor_map.get(textStyle['anchor'], MSO_VERTICAL_ANCHOR.TOP)

        if 'autofit' in textStyle:
            if textStyle['autofit']:
                textFrame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            else:
                textFrame.auto_size = MSO_AUTO_SIZE.NONE

        # Apply paragraph-level styles
        for i, paragraphData in enumerate(textStyle.get('paragraphs', [])):
            # Ensure the paragraph exists
            if i >= len(textFrame.paragraphs):
                paragraph = textFrame.add_paragraph()
            else:
                paragraph = textFrame.paragraphs[i]

            # Apply paragraph properties
            if 'level' in paragraphData:
                paragraph.level = int(paragraphData['level']) if paragraphData['level'] is not None else 0

            # Apply runs (text segments)
            paragraph.clear()  # Clear any existing runs
            for runData in paragraphData.get('runs', []):
                run = paragraph.add_run()
                run.text = text
                rPr = run.font

                # Apply font properties for the run
                if fontSizePt:
                    rPr.size = fontSizePt  # Use the pre-adjusted font size

                if 'language' in runData:
                    run.language_id = runData['language']
                if 'fontTypeface' in textStyle.get(f"level{paragraph.level + 1}", {}):
                    rPr.name = textStyle[f"level{paragraph.level + 1}"]['fontTypeface']
                if 'fontColor' in textStyle.get(f"level{paragraph.level + 1}", {}):
                    fontColor = textStyle[f"level{paragraph.level + 1}"]['fontColor']
                    if fontColor.startswith('#'):
                        rPr.color.rgb = RGBColor.from_string(fontColor[1:])
                    elif fontColor.startswith('RGB'):
                        rgb = fontColor[4:-1].split(',')
                        rPr.color.rgb = RGBColor(int(rgb[0]), int(rgb[1]), int(rgb[2]))

                # Apply other run styles
                if 'bold' in textStyle.get(f"level{paragraph.level + 1}", {}):
                    rPr.bold = textStyle[f"level{paragraph.level + 1}"]['bold'] == '1'
                break

        # Apply list level styles (e.g., margins, alignment) for each level
        for level in range(1, 10):
            levelKey = f"level{level}"
            if levelKey in textStyle:
                levelStyles = textStyle[levelKey]
                for paragraph in textFrame.paragraphs:
                    try:
                        if paragraph.level == level - 1:
                            if 'marginLeft' in levelStyles:
                                paragraph.margin_left = Inches(float(levelStyles['marginLeft']) / 914400)  # EMUs to Inches
                            if 'indent' in levelStyles:
                                paragraph.space_before = Inches(float(levelStyles['indent']) / 914400)  # EMUs to Inches
                            if 'alignment' in levelStyles:
                                alignmentMap = {
                                    'l'      : PP_ALIGN.LEFT,
                                    'ctr'    : PP_ALIGN.CENTER,
                                    'r'      : PP_ALIGN.RIGHT,
                                    'justify': PP_ALIGN.JUSTIFY
                                    }
                                paragraph.alignment = alignmentMap.get(levelStyles['alignment'], PP_ALIGN.LEFT)
                    except Exception as styleError:
                        print(f'Error applying the style from template {text}, {textBox}, {layoutPlaceholder}. Error: {styleError}')

    def _addTextToTextBox(self, text, textBox, layoutPlaceholder):
        """Adjust the font size of the text to ensure it fits in the given text box."""
        # Get text style
        textStyle = self.getTextStyle(layoutPlaceholder)
        textFrame = textBox.text_frame
        # Retrieve container height and width
        containerHeight = textBox.height
        containerWidth = textBox.width
        # Default font size (use the default or initial size from the style)
        # Note multi level is not yet enable yet, similarly to bullet points, not yet picked up correctly.
        fontSize = textStyle.get('level1', {}).get('fontSize')
        if fontSize is None:
            fontSize = textStyle.get('defaultFontSize', 12)  # Assume 12pt as a default
        # Set the initial font size
        fontSizePt = Pt(fontSize)
        # Create a function to estimate the total text height (in points)
        def _estimateTextHeight(text, fontSizePt, containerWidth):
            """Estimate the total height of the text based on the font size and text length."""
            estimatedHeight = 0
            lines = text.split('\n')  # Split the text into lines
            # Estimate the height per line (using the font size)
            lineHeight = fontSizePt * 1.2  # 1.2 multiplier for line spacing (can be adjusted)
            for line in lines:
                # Estimate the width of the line based on the number of characters
                # This is a simplification, and you could improve it by taking actual font metrics into account
                numChars = len(line)
                lineWidth = numChars * fontSizePt / 2  # Approximate character width (can adjust multiplier)
                # If line width exceeds the container width, we would need to break it into more lines
                if lineWidth > containerWidth:
                    # Estimate how many lines are needed
                    numLines = (lineWidth // containerWidth) + 1
                    estimatedHeight += numLines * lineHeight
                else:
                    # If it fits in one line, just add the line height
                    estimatedHeight += lineHeight
            return estimatedHeight

        # Estimate the text height with the initial font size
        estimatedHeight = _estimateTextHeight(text, fontSizePt, containerWidth)
        # Check if estimated height exceeds the available space
        while estimatedHeight > containerHeight and fontSizePt > Pt(1):  # Ensure font doesn't go below 1pt
            fontSizePt -= Pt(1)  # Reduce font size by 1pt
            estimatedHeight = _estimateTextHeight(text, fontSizePt, containerWidth)  # Recalculate height

        # Apply the adjusted font size to the text style
        self._insertTextAndApplyStyle(text, textBox, layoutPlaceholder, fontSizePt)  # Pass the adjusted font size

    def applyTableStyle(self, table):
        # Apply style for header row (first row)
        headerRow = table.rows[0]
        styleDict = self.tableStyleOptions
        h_alignment_map = {
            "left"      : PP_ALIGN.LEFT,
            "right"     : PP_ALIGN.RIGHT,
            "center"    : PP_ALIGN.CENTER,
            "justify"   : PP_ALIGN.JUSTIFY,
            "distribute": PP_ALIGN.DISTRIBUTE
            }
        v_alignment_map = {
            "top"        : MSO_ANCHOR.TOP,
            "middle"     : MSO_ANCHOR.MIDDLE,
            "bottom"     : MSO_ANCHOR.BOTTOM,
            }
        for cell in headerRow.cells:
            cell.text_frame.paragraphs[0].font.size = Pt(styleDict["header_font_size"])
            cell.text_frame.paragraphs[0].font.name = styleDict["header_font_name"]
            cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(*styleDict["header_font_color"])
            cell.text_frame.paragraphs[0].font.bold = styleDict["header_bold"]
            alignment = h_alignment_map.get(styleDict.get('header_h_alignment', 'center'), PP_ALIGN.CENTER) # center default
            cell.text_frame.paragraphs[0].alignment = alignment
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(*styleDict["header_background_color"])
            # Apply padding for header cells
            cell.margin_top = styleDict["cell_padding"]
            cell.margin_bottom = styleDict["cell_padding"]
            cell.margin_left = styleDict["cell_padding"]
            cell.margin_right = styleDict["cell_padding"]
            vertical_anchor = v_alignment_map.get(styleDict.get('header_v_alignment', 'middle'), MSO_ANCHOR.MIDDLE)  # middle default
            cell.vertical_anchor = vertical_anchor
            #  border styling seems not working

        # Apply style for all rows except the header
        for rowIndex, row in enumerate(list(table.rows)[1:], start=1):
            for colIndex, cell in enumerate(row.cells):
                # cell.text_frame.word_wrap = True
                # cell.text_frame.auto_size = None  # Disable auto-size
                cell.text_frame.paragraphs[0].font.size = Pt(styleDict["font_size"])
                cell.text_frame.paragraphs[0].font.name = styleDict["font_name"]
                cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(*styleDict["font_color"])
                cell.text_frame.paragraphs[0].font.bold = styleDict["bold"]
                cell.text_frame.paragraphs[0].alignment = h_alignment_map.get(styleDict.get('h_alignment', 'center'), PP_ALIGN.CENTER)  # center default

                # Alternating row background colors
                if rowIndex % 2 == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(*styleDict["cell_background_alternate_color"])
                else:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(*styleDict["cell_background_color"])

                # Apply padding for table cells
                cell.margin_top = styleDict["cell_padding"]
                cell.margin_bottom = styleDict["cell_padding"]
                cell.margin_left = styleDict["cell_padding"]
                cell.margin_right = styleDict["cell_padding"]

                # Set vertical alignment  for cells
                cell.vertical_anchor = v_alignment_map.get(styleDict.get('v_alignment', 'middle'), MSO_ANCHOR.MIDDLE)  # middle default

