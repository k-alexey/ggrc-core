/*
 Copyright (C) 2020 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import loLast from 'lodash/last';
import loIsEmpty from 'lodash/isEmpty';
import * as StateUtils from './state-utils';
import QueryParser from '../../generated/ggrc-filter-query-parser';
import {makeRelevantFilter} from './query-api-utils';

/**
 * Factory allowing to create Advanced Search Filter Items.
 */
export const create = {
  /**
   * Creates Filter Attribute.
   * @param {object} value - Filter Attribute data.
   * @param {object} options - List of options for attribute.
   * @return {object} - Attribute model.
   */
  attribute: (value, options = null) => {
    return {
      type: 'attribute',
      value: value || { },
      options,
    };
  },
  /**
   * Creates Group.
   * @param {Array} value - Group data.
   * @return {object} - Group model.
   */
  group: (value) => {
    return {
      type: 'group',
      value: value || [],
    };
  },
  /**
   * Creates Operator.
   * @param {string} value - Operator name.
   * @param {object} options - List of options for operator.
   * @return {object} - Operator model.
   */
  operator: (value, options = null) => {
    return {
      type: 'operator',
      value: value || '',
      options,
    };
  },
  /**
   * Creates Filter State
   * @param {object} value - State data.
   * @return {object} - State model.
   */
  state: (value) => {
    return {
      type: 'state',
      value: value || { },
    };
  },
  /**
   * Creates Mapping Criteria
   * @param {object} value - Mapping Criteria data.
   * @return {object} - Mapping Criteria model.
   */
  mappingCriteria: (value) => {
    return {
      type: 'mappingCriteria',
      value: value || { },
    };
  },
  parentInstance: (value) => {
    return {
      type: 'parentInstance',
      value: value || { },
    };
  },
};

/**
 * Adds Mapping Criteria as separate QueryAPI request.
 * @param {object} mapping - Mapping Criteria model value.
 * @param {Array} request - Collection of QueryAPI sub-requests.
 * @return {number} - QueryAPI request id.
 */
export const addMappingCriteria = (mapping, request) => {
  let filterObject = builders.attribute(mapping.filter.value);

  if (mapping.mappedTo) {
    let relevantResult =
      builders[mapping.mappedTo.type](mapping.mappedTo.value, request);
    filterObject = QueryParser.joinQueries(filterObject, relevantResult);
  }

  request.push({
    object_name: mapping.objectName,
    type: 'ids',
    filters: filterObject,
  });

  return request.length - 1;
};

/**
 * Convertes collection of Advanced Search models to reverse polish notation.
 * @param {Array} items - Collection of Advanced Search models.
 * @return {Array} - Collection of Advanced Search models sorted in reverse polish notation.
 */
export const reversePolishNotation = (items) => {
  const result = [];
  const stack = [];
  const priorities = {
    OR: 1,
    AND: 2,
  };

  items.forEach((item) => {
    if (item.type !== 'operator') {
      result.push(item);
    } else {
      if (!loIsEmpty(stack) &&
        priorities[item.value] <= priorities[loLast(stack).value]) {
        result.push(stack.pop());
      }
      stack.push(item);
    }
  });

  while (stack.length) {
    result.push(stack.pop());
  }

  return result;
};

/**
 * Contains QueryAPI filter expression builders.
 */
export const builders = {
  /**
   * Transforms Filter Attribute model to valid QueryAPI filter expression.
   * @param {object} attribute - Filter Attribute model value.
   * @return {object} - Valid QueryAPI filter expression.
   */
  attribute: (attribute) => {
    return {
      expression: {
        left: attribute.field,
        op: {name: attribute.operator},
        right: attribute.value.trim(),
      },
    };
  },
  /**
   * Transforms State model to valid QueryAPI filter expression.
   * @param {object} state - State model value.
   * @return {object} - Valid QueryAPI filter expression.
   */
  state: (state) => {
    let inverse = state.operator === 'NONE';
    return StateUtils.buildStatusFilter(
      state.items,
      state.modelName,
      inverse,
      state.statesCollectionKey
    );
  },
  /**
   * Transforms Group model to valid QueryAPI filter expression.
   * @param {array} items - Group model value.
   * @param {Array} request - Collection of QueryAPI sub-requests.
   * @return {object} - Valid QueryAPI filter expression.
   */
  group: (items, request) => {
    items = reversePolishNotation(items);

    const stack = [];
    items.forEach((item) => {
      if (item.type !== 'operator') {
        stack.push(builders[item.type](item.value, request));
      } else {
        let joinedValue = QueryParser.
          joinQueries(stack.pop(), stack.pop(), item.value);
        stack.push(joinedValue);
      }
    });

    return stack.pop() || {expression: {}};
  },
  /**
   * Transforms Mapping Criteria model to valid QueryAPI filter expression.
   * @param {object} criteria - Mapping Criteria model value.
   * @param {Array} request - Collection of QueryAPI sub-requests.
   * @return {object} - Valid QueryAPI filter expression.
   */
  mappingCriteria: (criteria, request) => {
    let criteriaId = addMappingCriteria(criteria, request);
    return {
      expression: {
        object_name: '__previous__',
        op: {name: 'relevant'},
        ids: [criteriaId],
      },
    };
  },
  parentInstance: (parentInstance) => {
    return makeRelevantFilter(parentInstance);
  },
};

/**
 * Builds QueryAPI valid filter expression based on Advanced Search models.
 * @param {Array} data - Collection of Advanced Search models.
 * @param {Array} request - Collection of QueryAPI sub-requests.
 * @return {object} - valid QueryAPI filter expression.
 */
export const buildFilter = (data, request) => {
  let result = builders.group(data, request);
  return result;
};

/**
 * Fills statusItem with default values for passed modelName.
 * @param {String} modelName - Name of the model to find states of.
 * @param {Symbol=} statesCollectionKey - describes key of collection with
 * states for certain model.
 * @return {canMap} - updated state.
 */
export const setDefaultStatusConfig = (
  modelName,
  statesCollectionKey = null
) => {
  const items = StateUtils.getStatesForModel(modelName, statesCollectionKey);

  return {
    items,
    modelName,
    statesCollectionKey,
    operator: 'ANY',
  };
};

const getSerializedAttribute = (model, parentAttrName, attrName) => {
  const attribute = parentAttrName ? `${parentAttrName}.${attrName}` : attrName;
  return model.attr(attribute)
    && model.attr(attribute).serialize();
};

export const getFilters = (model, parentAttrName) => {
  const filterItems =
  getSerializedAttribute(model, parentAttrName, 'filterItems');
  const mappingItems =
  getSerializedAttribute(model, parentAttrName, 'mappingItems');
  const statusItem =
  getSerializedAttribute(model, parentAttrName, 'statusItem');
  const parentInstance =
   getSerializedAttribute(model, parentAttrName, 'parentInstance');
  let parentItems =
  getSerializedAttribute(model, parentAttrName, 'parentItems');

  /*
  "parentInstance" - current parent instance (when sitting on some object page).
    For example: "Audit" instance is always parent instance for Assessments, when
    sitting on Audit page, Assessments tab.
  "parentItems" - parent instances from previous contexts.
    For example:
      1. Open any Regulation page (for example: "Regulation #1").
      2. Open "Programs" tab.
      3. Open advanced saved search.
      4. Filter contains text: "MAPPED TO REGULATION: Regulation #1".
        It happens because "Regulation #1" is parent instance for programs.
      5. Save current search (for example: "Saved search #1").
      6. Open any Objective page (for example: "Objective #1").
      7. Open "Programs" tab.
      8. Open advanced saved search.
      9. Filter contains text: "MAPPED TO OBJECTIVE: Objective #1".
        It happens because "Objective #1" is parent instance for programs right
        now.
      10. Select previously saved search from point 5 ("Saved search #1").
      11. Filter contains text:
        - "MAPPED TO OBJECTIVE: Objective #1"
        - "MAPPED TO REGULATION: Regulation #1".

    In this case "Objective #1" is current Parent Instance and "Regulation #1" is
    previous Parent Instance that was saved in step 5 and now is item in Parent
    Items.

    "parentItems" array can contain 0 - n items.
    Depends on previously saved search
  */
  if (parentInstance) {
    if (parentItems) {
      parentItems.push(parentInstance);
    } else {
      parentItems = [parentInstance];
    }
  }

  return {
    filterItems,
    mappingItems,
    statusItem,
    parentItems,
  };
};

/**
 * Build permalink for saved search
 * @param {Number} searchId - saved search ID
 * @param {String} widgetId - widget id
 * @return {String} - permalink
 */
export const buildSearchPermalink = (searchId, widgetId) => {
  const origin = window.location.origin;
  const pathName = window.location.pathname;
  const url = `${origin}${pathName}`;
  const hash = `#!${widgetId}&saved_search=${searchId}`;
  const permalink = `${url}${hash}`;

  return permalink;
};

/**
 * Convert JSON filter to Object
 * @param {string} json - JSON string
 * @return {Object} - parsed advanced search filter
 */
export const parseFilterJson = (json) => {
  let {
    filterItems,
    mappingItems,
    statusItem,
    parentItems,
  } = JSON.parse(json);

  return {
    filterItems,
    mappingItems,
    statusItem,
    parentItems,
  };
};
