"""
    python-pptx is a Python library for creating, modifying, and extracting data from PowerPoint (.pptx) files.

    Hierarchy:
    •	Presentation: Represents the whole PowerPoint file.
        •	Slide Masters: Templates that define the global layout and design for the slides.
            •	Slide Layouts: Predefined slide formats based on a slide master. These layouts are used for creating individual slides.
                    •	Shapes: Objects that can be added to a slide (e.g., text boxes, tables, images).
                        •	Placeholders: Predefined content areas on a slide layout (e.g., title, body text, image, etc.).

NB: For simplicity and practicality is often used only one single slide master in presentations, therefore also here we use only the first slide master and its layouts as template
Multiple slide masters are messy and maybe used for Complex Presentations or joint presentations...

A PPTx writer consists of two main python objects:
The PresentationWriter and  PPTxTemplate.
The first , PresentationWriter, is the general handler, and wraps/interacts to the  pptx python package
The second, PPTxTemplateMapper,  translates the actual .pptx file template to the final user .pptx report. So it will have methods to fetch the placeholder names
 and fill the new .pptx  file  with elements from ccpn.

"""

import pandas as pd
import matplotlib.pyplot as plt
from abc import abstractmethod
from collections import defaultdict
from typing import Union, cast
from pptx import Presentation as _presentation
from pptx.slide import Slides, Slide, SlideLayout
from pptx.shapes.placeholder import LayoutPlaceholder
from ccpn.util.Path import aPath, checkFilePath
from ccpn.util.Logging import getLogger
from ccpn.util.pptx.PPTxStyleManager import PPTStyleManager


PLACEHOLDER_NAME = 'placeholder_name'
PLACEHOLDER_TYPE = 'placeholder_type'
PLACEHOLDER_GETTER = 'placeholder_getter'
PLACEHOLDER_SETTER = 'placeholder_setter'
PLACEHOLDER_STYLE_GETTER = 'placeholder_style_getter'
PLACEHOLDER_STYLE_SETTER = 'placeholder_style_setter'

PLACEHOLDER_TYPE_TEXT = 'Text'
PLACEHOLDER_TYPE_IMAGE = 'Image'
PLACEHOLDER_TYPE_TABLE = 'Table'


class PPTxPresentationWriter():

    def __init__(self, presentationTemplate, placeholderErrorPolicy='raise'):
        """
        :param pptxPath: The path to an existing PPTx presentation containing a single slide master and layout(s) with appropriately
                                     named placeholders to use as a template for a new presentation.
        """
        self._presentationTemplate = presentationTemplate
        self._pptxPath = self._presentationTemplate.getAbsoluteTemplatePath()
        self._presentation = _presentation(self._pptxPath)
        self._placeholderErrorPolicy = placeholderErrorPolicy
        self._data = None

        if len(self._presentation.slide_masters)>1:
            raise RuntimeWarning('Multiple slide masters are not supported. This  Presentation will use only the first slide master')
        self.styleManager = PPTStyleManager(self)

    @property
    def data(self):
        return self._data

    def setData(self, **kwargs):
        self._data = {**kwargs} # This creates a shallow copy of the kwargs dictionary instead of data = kwargs (that points to the same passed in dict)

    @abstractmethod
    def buildFromTemplate(self):
        """
        Builds a new presentation based on the template, dynamically applying content to placeholders
        as defined in the slide mapping.
        """
        self._presentationTemplate.setData(**self.data)
        isValidTemplate, templateErrors = self._validateTemplate()
        if not isValidTemplate and self._placeholderErrorPolicy == 'raise':
            raise RuntimeError(f'Detected errors while building a new Presentation from Template \n{self._formatDefaultDict(templateErrors)}')
        else:

            slideMapping = self._presentationTemplate.slideMapping
            for slideLayoutName, placeholderDefs in slideMapping.items():
                layout = self.getLayout(slideLayoutName)
                newSlide = self.newSlide(layout, removePlaceholders=True)
                for placeholderDef in placeholderDefs:
                    try:
                        self._handlePlaceholder(newSlide, layout, placeholderDef)
                    except Exception as ex:
                        print(f'Some Error in filling the placeholder occurred: {ex}')

    def save(self, filePath):
        self._presentation.save(filePath)

    def newSlide(self, layoutIdentifier: Union[SlideLayout, int, str], removePlaceholders: bool=True) -> Slide:
        """
        A method to add slide and clone (if necessary) the placeholder from the master slide .
        Defaults remove all newly generated placeholders. This is intentional because there are too many issues/bugs in the release of pptx used when creating this class.
        Furthermore, placeholders   in the new slides are confusing with the master layout placeholders, because not exactly as the template.
        Pptx when cloning the placeholders gives new names and shape ids and makes impossible to back-track the original placeholder names, defeating
        the whole reason naming placeholders in the master template! The only way to find it back seems by matching by placeholder.element.ph_idx [ Took a while to spot this! ]
        If we keep the placeholders, We need to rename them to match the placeholder from the master slide.
        :return: a new slide
        """
        if layoutIdentifier is None:
            raise ValueError("A layout must be provided.")
        if isinstance(layoutIdentifier, SlideLayout):
            layout = layoutIdentifier
        elif isinstance(layoutIdentifier, (int, str)):
            layout = self.getLayout(layoutIdentifier)
        else:
            raise ValueError("The layoutIdentifier parameter must be a SlideLayout, int, or str.")

        newSlide = self._presentation.slides.add_slide(layout)
        if removePlaceholders:
            self._removePlaceholdersForSlide(newSlide)
        else:
            self._matchPlaceholdersNameToLayout(newSlide, layout)
        return newSlide

    def getSlides(self) -> tuple[Slide, ...]:
        """A list of slides of this presentation."""
        sldIdLst = self._presentation._element.get_or_add_sldIdLst()
        self._presentation.part.rename_slide_parts([cast("CT_SlideId", sldId).rId for sldId in sldIdLst])
        return tuple([slide for slide in Slides(sldIdLst, self._presentation)])

    def getLayout(self, identifier: int | str = 0) -> SlideLayout:
        """
        Retrieve a slide layout by index or name.

        :param identifier: Either an integer (layout index) or a string (layout name).
        :return: The slide layout object.
        :raises ValueError: If the identifier is invalid or out of range.
        :raises RuntimeError: If a name is provided but no matching layout is found.
        """
        layouts = self._presentation.slide_layouts

        # Handle identifier as an integer (index)
        if isinstance(identifier, int):
            if 0 <= identifier < len(layouts):
                return layouts[identifier]
            raise ValueError(f"Layout index {identifier} is out of range. Valid indices: 0-{len(layouts) - 1}")

        # Handle identifier as a string (name)
        elif isinstance(identifier, str):
            for layout in layouts:
                if layout.name == identifier:
                    return layout
            raise RuntimeError(f"Could not find a layout called: {identifier}")

        # Invalid identifier type
        raise ValueError("Identifier must be an integer (index) or a string (name).")

    def getLayoutPlaceholders(self, layoutIdentifier: Union[SlideLayout, int, str]) -> dict[str, LayoutPlaceholder]:
        """
        Retrieve the placeholders from a slide layout.

        :param layoutIdentifier: The slide layout, identified by one of the following:
                                  - SlideLayout object
                                  - Integer (layout index)
                                  - String (layout name)
        :return: A dictionary of placeholders in the specified layout.
        """
        if layoutIdentifier is None:
            raise ValueError("A layout must be provided.")
        if isinstance(layoutIdentifier, SlideLayout):
            slideLayout = layoutIdentifier
        elif isinstance(layoutIdentifier, (int, str)):
            slideLayout = self.getLayout(layoutIdentifier)
        else:
            raise ValueError("The layoutIdentifier parameter must be a SlideLayout, int, or str.")
        return {placeholder.name: placeholder for placeholder in slideLayout.placeholders if placeholder.is_placeholder and placeholder.name}

    def insertText(self, targetSlide, templateLayout, placeholderName, text):
        """Inserts text into a PowerPoint slide using an existing placeholder shape."""
        layoutPlaceholder = self._getLayoutPlaceholder(placeholderName, templateLayout)
        left, top, width, height = self._getLayoutPlaceholderCoords(layoutPlaceholder)
        textBoxShape = targetSlide.shapes.add_textbox(left, top, width, height)
        self.styleManager._addTextToTextBox(text, textBoxShape, layoutPlaceholder)
        return textBoxShape

    def insertDataFrame(self, targetSlide, templateLayout, placeholderName, dataFrame, fontSize=7):
        """Converts a Pandas DataFrame to a PowerPoint table using an existing shape.
        """
        layoutPlaceholder = self._getLayoutPlaceholder(placeholderName, templateLayout)
        colnames = list(dataFrame.columns)
        rows, cols = dataFrame.shape

        # Get position and size from placeholder
        left, top, width, height = self._getLayoutPlaceholderCoords(layoutPlaceholder)

        # Create the table in the slide with same position and size as the placeholder
        tableShape = targetSlide.shapes.add_table(rows + 1, cols, left, top, width, height)  # +1 for header row
        table = tableShape.table

        # Fill in the column headers (first row)
        for colIndex, colName in enumerate(colnames):
            cell = table.cell(0, colIndex)
            cell.text = colName
            # Make headers bold (optional)
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True

        # Fill in the DataFrame values (starting from the second row)
        for rowIndex, (index, row) in enumerate(dataFrame.iterrows(), start=1):  # start=1 to begin after header row
            for colIndex, val in enumerate(row):
                table.cell(rowIndex, colIndex).text = str(val)
        # Set style for all cells
        self.styleManager.applyTableStyle(table)

    def insertImage(self, targetSlide, templateLayout, placeholderName, imagePath):

        layoutPlaceholder = self._getLayoutPlaceholder(placeholderName, templateLayout)
        # Get master placeholder's dimensions
        left, top, width, height = self._getLayoutPlaceholderCoords(layoutPlaceholder)

        imageWidth, imageHeight = self._getImageSize(imagePath)
        imageHeight = imageHeight or 300 #px default fallback
        imageWidth = imageWidth or 300
        # Calculate the aspect ratio of the image
        imageRatio = imageWidth / imageHeight
        placeholderRatio = width / height

        # Scale the image to fit within the placeholder
        if imageRatio > placeholderRatio:
            # Fit by width
            scaledWidth = width
            scaledHeight = int(width / imageRatio)
        else:
            # Fit by height
            scaledHeight = height
            scaledWidth = int(height * imageRatio)

        # Center the scaled image within the placeholder
        centeredLeft = left + (width - scaledWidth) // 2
        centeredTop = top + (height - scaledHeight) // 2

        # Add the scaled and centered image to the slide
        targetSlide.shapes.add_picture(
                imagePath,
                centeredLeft,
                centeredTop,
                width=scaledWidth,
                height=scaledHeight,
                )

    @staticmethod
    def _getImageSize(filePath):
        try:
            image = plt.imread(filePath)
            height, width = image.shape[:2]  # First two dimensions are height and width
            return width, height
        except Exception as err:
            getLogger().debug(f'Cannot get image size for {filePath}. Error: {err}')
            return None, None

    @staticmethod
    def _formatDefaultDict(d):
        items = "\n".join(f"  {repr(k)}: {repr(v)}," for k, v in d.items())
        return f"{{\n{items}\n}}"

    def _validateTemplate(self):
        """
        Examine the template SlideMapping and ensure names are properly defined and any getter/setter exists
        """
        errorMsgDict = defaultdict(list)
        slideMapping = self._presentationTemplate.slideMapping
        for slideLayoutName, placeholderDefs in slideMapping.items():
            layout = None
            try:
                layout = self.getLayout(slideLayoutName)
            except ValueError as err:
                errorMsgDict[slideLayoutName].append(err)
            if layout is not None:
                for placeholderDef in placeholderDefs:
                    placeholderName = placeholderDef.get(PLACEHOLDER_NAME)
                    placeholderType = placeholderDef.get(PLACEHOLDER_TYPE)
                    placeholderGetter = placeholderDef.get(PLACEHOLDER_GETTER)
                    ph = None
                    try:
                        ph = self._getLayoutPlaceholder(placeholderName, layout)
                    except ValueError as phErr:
                        errorMsgDict[(slideLayoutName, placeholderName)].append(phErr)

                    if ph:
                        getterFunc = getattr(self._presentationTemplate, placeholderGetter, None)
                        if getterFunc is None:
                            errorMsgDict[(slideLayoutName, placeholderName)].append(f'Could not find a valid getter: {placeholderGetter} is not defined in the template Class')
                        #  we have getter  in the class . now er need to check  the value returned is the same type from the one defined in the mapping
                        else:
                            try:
                                value = getterFunc()
                                if isinstance(value, str) and placeholderType in [PLACEHOLDER_TYPE_TEXT, PLACEHOLDER_TYPE_IMAGE]:
                                    continue
                                elif isinstance(value, pd.DataFrame) and placeholderType in [PLACEHOLDER_TYPE_TABLE]:
                                    continue
                                else:
                                    errorMsgDict[(slideLayoutName, placeholderName)].append(f'The placeholder Type is not same as getter')
                            except Exception as _ex:
                                errorMsgDict[(slideLayoutName, placeholderName)].append(f'Error retrieving the placeholder value. {_ex}')

        isValid = True if len(errorMsgDict) == 0 else False
        return isValid, errorMsgDict


    def _getLayouts(self):
        """
        Get the master slide layouts. Layouts contain the master placeholders used to create any new slides
        :return: list of slide layouts
        """
        return [slide for slide in self._presentation.slide_layouts]

    def slideWidth(self):
        return self._presentation.slide_width

    def setSlideWidth(self, width):
        self._presentation.slide_width = width

    def slideHeight(self):
        return self._presentation.slide_height

    def setSlideHeight(self, height):
        self._presentation.slide_height = height

    def _matchPlaceholdersNameToLayout(self, slide, layout):
        for newPlaceholder in slide.placeholders:
            for masterPlaceholder in layout.placeholders:
                if masterPlaceholder.element.ph_idx == newPlaceholder.element.ph_idx:
                    newPlaceholder.name = masterPlaceholder.name

    def _removePlaceholdersForSlide(self, slide):
        for shape in list(slide.shapes):  # Convert to list to avoid modification issues
            if shape.is_placeholder:
                shapePlaceholderFormat = shape.placeholder_format
                shapePlaceholderFormat.element.getparent().remove(shapePlaceholderFormat.element)
        return slide

    def _getLayoutPlaceholder(self, placeholderName, templateLayout) -> LayoutPlaceholder:
        layoutPlaceholders = self.getLayoutPlaceholders(templateLayout)
        layoutPlaceholder = layoutPlaceholders.get(placeholderName, None)
        if layoutPlaceholder is None:
            raise ValueError(f'Could not find the placeholder called {placeholderName}')
        return layoutPlaceholder

    def _getLayoutPlaceholderCoords(self, placeholder):
        left = placeholder.left
        top = placeholder.top
        width = placeholder.width
        height = placeholder.height
        return (left, top, width, height)

    def _handlePlaceholder(self, slide, layout, placeholderDef,  **getterKwargs):
        """
        Handles insertion of content into a placeholder based on its type.
        """
        placeholderName = placeholderDef.get(PLACEHOLDER_NAME)
        placeholderType = placeholderDef.get(PLACEHOLDER_TYPE)
        placeholderGetter = placeholderDef.get(PLACEHOLDER_GETTER)
        # Dynamically retrieve the content for the placeholder
        getterFunc = getattr(self._presentationTemplate, placeholderGetter, None)
        if getterFunc is None:
            return
        value = getterFunc(**getterKwargs)
        if placeholderType == 'Text':
            self.insertText(slide, layout, placeholderName, value or '')
        elif placeholderType == PLACEHOLDER_TYPE_IMAGE:
            isPathOk, msgErr = checkFilePath(aPath(value))
            if isPathOk:
                self.insertImage(slide, layout, placeholderName, value)
        elif placeholderType == PLACEHOLDER_TYPE_TABLE:
            try:
                self.insertDataFrame(slide, layout, placeholderName, value)
            except Exception as err:
                print('Cannot add table', err)






class ScreeningPresentationWriter(PPTxPresentationWriter):
    """The top layer  object to create presentations from a PPTX template.  This subclass  allows to write slides using its specialised
    slide writer and additionally add a custom first page summary. """

    def buildFromTemplate(self):
        import ccpn.AnalysisScreen.lib.experimentAnalysis.matching.MatchingVariables as mv
        self._presentationTemplate.setData(**self.data)
        isValidTemplate, templateErrors = self._validateTemplate()
        if not isValidTemplate and self._placeholderErrorPolicy == 'raise':
            raise RuntimeError(f'Detected errors while building a new Presentation from Template \n{self._formatDefaultDict(templateErrors)}')
        else:
            slideMapping = self._presentationTemplate.slideMapping
            # build the title (first slide)
            if not slideMapping:
                raise RuntimeError(f'Detected errors while building a new Presentation from Template \n{self._formatDefaultDict(templateErrors)}')
            titleLayoutName = list(slideMapping.keys())[0]
            titlePlaceholderDefs = slideMapping[titleLayoutName]
            layout = self.getLayout(titleLayoutName)
            newSlide = self.newSlide(layout, removePlaceholders=True)
            for placeholderDef in titlePlaceholderDefs:
                try:
                    self._handlePlaceholder(newSlide, layout, placeholderDef)
                except Exception as ex:
                    print(f'Some Error in filling the placeholder occurred: {ex}')

            # build the substances Slides
            substanceTable = self.data.get('substanceTable')
            matchingTable = self.data.get('matchingTable')
            if substanceTable is None:
                return

            for i, (tableIndex, substanceTableRow) in enumerate(substanceTable.iterrows()):
                substancePid = substanceTableRow[mv.Reference_SubstancePid]
                matchingTableForSubstance = matchingTable[matchingTable[mv.Reference_SubstancePid]==substancePid]
                titleLayoutName = list(slideMapping.keys())[1]
                titlePlaceholderDefs = slideMapping[titleLayoutName]
                layout = self.getLayout(titleLayoutName)
                newSlide = self.newSlide(layout, removePlaceholders=True)
                for placeholderDef in titlePlaceholderDefs:
                    self._handlePlaceholder(newSlide, layout, placeholderDef,
                                            substanceTableIndex = i+1,
                                            substanceTableRow=substanceTableRow,
                                            matchingTableForSubstance=matchingTableForSubstance)



