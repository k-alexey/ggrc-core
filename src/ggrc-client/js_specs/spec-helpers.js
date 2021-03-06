/*
 Copyright (C) 2020 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

// This is primarily useful for passing as the fail case for
//  promises, since every item passed to it will show up in
//  the jasmine output.
function failAll(done) {
  return function (...args) {
    args.forEach(function (arg) {
      fail(JSON.stringify(arg));
    });
    if (done) {
      done();
    }
  };
}

function getComponentVM(Component) {
  // viewModel is CanMap
  if (Component.prototype.viewModel) {
    return new Component.prototype.viewModel();
  }

  // ViewModel is DefineMap
  const VM = Component.prototype.ViewModel;

  /*
    turn OFF "seal" flag to add possibility use "spyOn" jasmine function.
    Needs to override default behavior of ViewModel's method.
  */
  VM.seal = false;
  return new VM();
}

function makeFakeModel({model, staticProps = {}, instanceProps = {}} = {}) {
  const attrsForBaseModel = model.attributes;
  const staticPresetup = {
    // "attributes" isn't inherited from base model.
    // We should explicitly set the same "attributes" for derived models from
    // base model.
    attributes: {...attrsForBaseModel},
    ...staticProps,
  };

  return model.extend(staticPresetup, instanceProps);
}

function makeFakeInstance({
  model,
  staticProps = {},
  instanceProps = {},
} = {}) {
  const fakeModel = makeFakeModel({model, staticProps, instanceProps});
  return (...instanceArgs) => new fakeModel(...instanceArgs);
}

/**
 * Returns spy for get/set of passed 'property' in 'viewModel'.
 * This spy will be called on getting or setting value of this property e.g.
 * viewModel.attr(property), viewModel.attr(property, someValue).
 * get/set of this 'property' should be defined in viewModel through define plugin.

 * @param {canComponent.viewModel} viewModel
 * @param {string} property
 *
 * @returns {jasmine.Spy}
 */

function spyProp(viewModel, property) {
  const spy = jasmine.createSpy(`compute of ${property}`);

  viewModel._computedAttrs[property].compute = spy;

  return spy;
}

export {
  failAll,
  getComponentVM,
  makeFakeModel,
  makeFakeInstance,
  spyProp,
};
